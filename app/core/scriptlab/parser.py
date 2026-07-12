"""Span-preserving JS config parser for Script Lab.

Unlike the old tdcmodel ConfigParser (regex-extract → json.loads → minified
re-inject, which destroys comments/formatting), this parser records the exact
source span of every editable VALUE and writes changes back by splicing those
spans only — the rest of the file stays byte-identical.

Two tiers:
  Tier 1  top-level `const X = {...}` / `export const X = {...}` object
          literals (and scalar consts) → structured fields with key paths,
          Thai inline comments as labels, `// ==== section ====` headers.
  Tier 2  fallback for "inline style" scripts (no config object): numeric
          properties/consts that carry a trailing // comment.

Encoding: files are read as bytes and decoded utf-8 with surrogateescape so a
save with zero edits is always byte-identical (BOM and CRLF preserved).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path

# ---------------------------------------------------------------------------
# Scanner: mask strings/comments so structure can be walked naively.
# ---------------------------------------------------------------------------

@dataclass
class Comment:
    start: int
    end: int
    text: str      # without // or /* */
    line: int
    block: bool


def _scan(src: str) -> tuple[str, list[Comment]]:
    """Return (masked, comments).

    masked: same length as src; string contents and whole comments become
    spaces (quotes kept, newlines kept) so brace/comma walking is safe.
    """
    n = len(src)
    out = list(src)
    comments: list[Comment] = []
    i = 0
    line = 0
    # last non-space code char — for regex-literal heuristic
    prev_code = ""

    def blank(a: int, b: int, keep_nl: bool = True) -> None:
        for k in range(a, b):
            if not (keep_nl and out[k] == "\n"):
                out[k] = " "

    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "/":
                j = src.find("\n", i)
                if j == -1:
                    j = n
                comments.append(Comment(i, j, src[i + 2:j].strip(), line, False))
                blank(i, j)
                i = j
                continue
            if nxt == "*":
                j = src.find("*/", i + 2)
                j = n if j == -1 else j + 2
                text = src[i + 2:j - 2] if j <= n else src[i + 2:]
                comments.append(Comment(i, j, text.strip(), line, True))
                start_line = line
                line += src.count("\n", i, j)
                blank(i, j)
                i = j
                continue
            # regex literal heuristic: '/' right after an operator/opener
            if prev_code in "(,=:[!&|?{};+-*%<>~^" or prev_code == "":
                j = i + 1
                in_class = False
                while j < n:
                    cj = src[j]
                    if cj == "\\":
                        j += 2
                        continue
                    if cj == "\n":
                        break  # not a regex after all
                    if cj == "[":
                        in_class = True
                    elif cj == "]":
                        in_class = False
                    elif cj == "/" and not in_class:
                        break
                    j += 1
                if j < n and src[j] == "/":
                    blank(i + 1, j)
                    i = j + 1
                    prev_code = "/"
                    continue
        if c in "'\"`":
            q = c
            j = i + 1
            while j < n:
                cj = src[j]
                if cj == "\\":
                    j += 2
                    continue
                if cj == q:
                    break
                if cj == "\n" and q != "`":
                    break
                j += 1
            blank(i + 1, min(j, n))
            line += src.count("\n", i, min(j + 1, n))
            i = min(j + 1, n)
            prev_code = q
            continue
        if not c.isspace():
            prev_code = c
        i += 1

    return "".join(out), comments


def _line_starts(src: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", src):
        starts.append(m.end())
    return starts


def _line_of(starts: list[int], pos: int) -> int:
    import bisect
    return bisect.bisect_right(starts, pos) - 1


# ---------------------------------------------------------------------------
# Field model
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_STR_RE = re.compile(r"^(['\"])(?:\\.|(?!\1).)*\1$", re.S)
_SECTION_RE = re.compile(r"^[=\-–—#*\s]*={2,}\s*(.+?)\s*={2,}[=\-\s]*$")


@dataclass
class Field:
    id: str
    path: str            # e.g. "CONFIG.punchDamage" or "DAMAGE.MOONLIGHT_BASE"
    key: str
    value: object        # python value for literals; raw text for readonly
    raw: str             # exact source text of the value
    type: str            # number | string | boolean | array | expr
    start: int
    end: int
    comment: str = ""
    section: str = ""
    readonly: bool = False
    quote: str = '"'     # original quote char for strings
    items: list | None = None   # for scalar arrays: [{raw, value, type}]


@dataclass
class ParseResult:
    fields: list[Field] = dc_field(default_factory=list)
    objects: list[str] = dc_field(default_factory=list)  # top-level names found
    tier: int = 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_IDENT = r"[A-Za-z_$][\w$]*"
_TOP_CONST_RE = re.compile(
    r"(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(" + _IDENT + r")\s*=\s*")
_FUNC_RE = re.compile(
    r"(?:function\s+(" + _IDENT + r")\s*\(" +
    r"|(?:const|let|var)\s+(" + _IDENT + r")\s*=\s*(?:async\s*)?\()")


class ScriptParser:
    def __init__(self, src: str):
        self.src = src
        self.masked, self.comments = _scan(src)
        self.starts = _line_starts(src)
        self._fid = 0
        # comments indexed by line for fast label lookup
        self.by_line: dict[int, list[Comment]] = {}
        for c in self.comments:
            self.by_line.setdefault(c.line, []).append(c)

    # -- helpers ------------------------------------------------------------

    def _next_id(self) -> str:
        self._fid += 1
        return f"f{self._fid}"

    def _skip_ws(self, i: int) -> int:
        m = self.masked
        while i < len(m) and m[i].isspace():
            i += 1
        return i

    def _match_brace(self, i: int) -> int:
        """i at '{' (or '['); return index of its matching closer."""
        opener = self.masked[i]
        closer = {"{": "}", "[": "]", "(": ")"}[opener]
        depth = 0
        m = self.masked
        for j in range(i, len(m)):
            if m[j] == opener:
                depth += 1
            elif m[j] == closer:
                depth -= 1
                if depth == 0:
                    return j
        return len(m) - 1

    def _depth0(self, pos: int) -> bool:
        """True if pos is at top level (no enclosing braces/parens/brackets)."""
        d = 0
        m = self.masked
        for j in range(pos):
            c = m[j]
            if c in "{[(":
                d += 1
            elif c in "}])":
                d -= 1
        return d == 0

    def _trailing_comment(self, value_end: int) -> str:
        ln = _line_of(self.starts, value_end - 1 if value_end > 0 else 0)
        for c in self.by_line.get(ln, []):
            if c.start >= value_end:
                return c.text
        return ""

    def _leading_comment(self, key_start: int) -> tuple[str, str]:
        """(label, section) from comment lines directly above the key."""
        ln = _line_of(self.starts, key_start)
        label_parts: list[str] = []
        section = ""
        row = ln - 1
        while row >= 0:
            cs = self.by_line.get(row, [])
            if not cs:
                break
            # line must be comment-only (masked shows only spaces)
            line_txt = self.masked[self.starts[row]: self.starts[row + 1] if row + 1 < len(self.starts) else len(self.masked)]
            if line_txt.strip():
                break
            text = cs[0].text
            sec = _SECTION_RE.match(text)
            if sec:
                section = sec.group(1)
                break
            label_parts.insert(0, text)
            row -= 1
        return " ".join(label_parts).strip(), section

    def _section_before(self, key_start: int, obj_start: int) -> str:
        """Nearest `// ==== X ====` header between obj_start and key."""
        best = ""
        for c in self.comments:
            if obj_start < c.start < key_start:
                m = _SECTION_RE.match(c.text)
                if m:
                    best = m.group(1)
        return best

    # -- value classification ------------------------------------------------

    def _classify(self, raw: str) -> tuple[str, object, bool, str]:
        """(type, value, readonly, quote)"""
        t = raw.strip()
        if _NUM_RE.match(t):
            v = float(t)
            if v.is_integer() and "." not in t and "e" not in t.lower():
                v = int(t)
            return "number", v, False, '"'
        if _STR_RE.match(t):
            q = t[0]
            inner = t[1:-1]
            inner = inner.replace("\\" + q, q).replace("\\\\", "\\").replace("\\n", "\n")
            return "string", inner, False, q
        if t in ("true", "false"):
            return "boolean", t == "true", False, '"'
        if t == "null":
            return "expr", t, True, '"'
        return "expr", t, True, '"'

    # -- object literal ------------------------------------------------------

    def parse_object(self, open_idx: int, path: str, out: list[Field]) -> None:
        m = self.masked
        close_idx = self._match_brace(open_idx)
        i = open_idx + 1
        while i < close_idx:
            i = self._skip_ws(i)
            if i >= close_idx:
                break
            if m[i] == ",":
                i += 1
                continue
            # key
            key_start = i
            if m[i] in "'\"":
                kq_end = self.src.find(m[i], i + 1)
                if kq_end == -1:
                    break
                key = self.src[i + 1:kq_end]
                i = kq_end + 1
            else:
                km = re.match(_IDENT, m[i:close_idx])
                if not km:
                    # can't parse (spread, method, etc.) → skip to next comma at this depth
                    i = self._skip_entry(i, close_idx)
                    continue
                key = km.group(0)
                i += len(key)
            i = self._skip_ws(i)
            if i >= close_idx or m[i] != ":":
                i = self._skip_entry(i, close_idx)
                continue
            i = self._skip_ws(i + 1)
            vs = i
            fpath = f"{path}.{key}" if path else key

            if m[i] == "{":
                ve = self._match_brace(i) + 1
                self.parse_object(i, fpath, out)
            elif m[i] == "[":
                ve = self._match_brace(i) + 1
                self._emit_array(key, fpath, vs, ve, out, open_idx)
            else:
                ve = self._scalar_end(i, close_idx)
                self._emit_scalar(key, fpath, vs, ve, out, open_idx)
            i = ve
        # done

    def _skip_entry(self, i: int, close_idx: int) -> int:
        m = self.masked
        depth = 0
        while i < close_idx:
            c = m[i]
            if c in "{[(":
                depth += 1
            elif c in "}])":
                depth -= 1
            elif c == "," and depth == 0:
                return i + 1
            i += 1
        return i

    def _scalar_end(self, i: int, close_idx: int) -> int:
        m = self.masked
        depth = 0
        j = i
        while j < close_idx:
            c = m[j]
            if c in "{[(":
                depth += 1
            elif c in "}])":
                if depth == 0:
                    break
                depth -= 1
            elif c in ",;\n" and depth == 0:
                break
            j += 1
        # trim trailing whitespace
        while j > i and self.src[j - 1].isspace():
            j -= 1
        return j

    def _emit_scalar(self, key: str, fpath: str, vs: int, ve: int,
                     out: list[Field], obj_start: int) -> None:
        raw = self.src[vs:ve]
        ftype, value, readonly, quote = self._classify(raw)
        comment = self._trailing_comment(ve)
        lead, _sec = self._leading_comment(vs)
        out.append(Field(
            id=self._next_id(), path=fpath, key=key, value=value, raw=raw,
            type=ftype, start=vs, end=ve,
            comment=comment or lead,
            section=self._section_before(vs, obj_start),
            readonly=readonly, quote=quote,
        ))

    def _emit_array(self, key: str, fpath: str, vs: int, ve: int,
                    out: list[Field], obj_start: int) -> None:
        inner_s, inner_e = vs + 1, ve - 1
        items = []
        i = inner_s
        ok = True
        while i < inner_e:
            i = self._skip_ws(i)
            if i >= inner_e:
                break
            if self.masked[i] in "{[":
                ok = False  # array of objects → readonly
                break
            j = self._scalar_end(i, inner_e)
            raw = self.src[i:j].strip()
            if raw:
                t, v, ro, q = self._classify(raw)
                if ro:
                    ok = False
                    break
                items.append({"raw": raw, "value": v, "type": t, "quote": q})
            i = j
            i = self._skip_ws(i)
            if i < inner_e and self.masked[i] == ",":
                i += 1
        raw_all = self.src[vs:ve]
        comment = self._trailing_comment(ve)
        lead, _sec = self._leading_comment(vs)
        out.append(Field(
            id=self._next_id(), path=fpath, key=key,
            value=[it["value"] for it in items] if ok else raw_all,
            raw=raw_all, type="array" if ok else "expr",
            start=vs, end=ve, comment=comment or lead,
            section=self._section_before(vs, obj_start),
            readonly=not ok, items=items if ok else None,
        ))

    # -- top level ------------------------------------------------------------

    def parse(self) -> ParseResult:
        res = ParseResult()
        covered: list[tuple[int, int]] = []

        for m in _TOP_CONST_RE.finditer(self.masked):
            name = m.group(1)
            vs = m.end()
            if not self._depth0(m.start(1)):
                continue
            vs = self._skip_ws(vs)
            if vs >= len(self.masked):
                continue
            c = self.masked[vs]
            if c == "{":
                ve = self._match_brace(vs) + 1
                self.parse_object(vs, name, res.fields)
                res.objects.append(name)
                covered.append((m.start(), ve))
            elif c == "[":
                ve = self._match_brace(vs) + 1
                self._emit_array(name, name, vs, ve, res.fields, m.start())
                res.objects.append(name)
                covered.append((m.start(), ve))
            else:
                ve = self._scalar_end(vs, len(self.masked))
                raw = self.src[vs:ve].strip()
                ftype, value, readonly, quote = self._classify(raw)
                if ftype in ("number", "string", "boolean"):
                    res.fields.append(Field(
                        id=self._next_id(), path=name, key=name, value=value,
                        raw=self.src[vs:ve], type=ftype, start=vs, end=ve,
                        comment=self._trailing_comment(ve),
                        readonly=readonly, quote=quote,
                    ))
                    covered.append((m.start(), ve))

        pre_tier2 = len([f for f in res.fields if not f.readonly])
        self._tier2(res)
        if pre_tier2 == 0 and len(res.fields) > 0:
            res.tier = 2
        return res

    # -- tier 2: values everywhere else --------------------------------------
    #
    # Catches what the structured walk can't: values inside functions,
    # let/var-assigned objects, and members of array-of-objects (readonly in
    # tier 1). Grouped by the innermost enclosing function so skill code reads
    # as its own section — this is what makes "any script style" work.

    def _functions(self) -> list[tuple[str, int, int]]:
        """(name, body_start, body_end) for every function-ish declaration."""
        out = []
        m = self.masked
        for match in _FUNC_RE.finditer(m):
            name = match.group(1) or match.group(2)
            # find the body '{' after the parameter list closes
            i = m.find("(", match.start())
            if i == -1:
                continue
            close_paren = self._match_brace(i)
            j = close_paren + 1
            # skip over `=> ` / whitespace
            while j < len(m) and m[j] in " \t\r\n=>":
                j += 1
            if j < len(m) and m[j] == "{":
                out.append((name, j, self._match_brace(j)))
        return out

    def _tier2(self, res: ParseResult) -> None:
        # spans of values already editable via tier 1 — never duplicate those
        editable_spans = [(f.start, f.end) for f in res.fields if not f.readonly]
        # readonly tier-1 fields (e.g. array-of-objects) — their inside IS fair
        # game; remember them to label the section nicely
        ro_fields = [f for f in res.fields if f.readonly]
        funcs = self._functions()

        def in_editable(pos: int) -> bool:
            return any(a <= pos < b for a, b in editable_spans)

        def section_for(pos: int) -> str:
            for f in ro_fields:
                if f.start <= pos < f.end:
                    return f.path
            best = ""
            best_len = None
            for name, a, b in funcs:
                if a <= pos < b and (best_len is None or b - a < best_len):
                    best, best_len = name, b - a
                if a > pos:
                    break
            return f"ฟังก์ชัน {best}()" if best else "ค่าอื่นๆ ในโค้ด"

        pat = re.compile(
            r"(" + _IDENT + r")\s*[:=]\s*"
            r"(-?(?:\d+\.?\d*|\.\d+)(?![\w.])|true|false|(['\"]))")
        count = 0
        for m in pat.finditer(self.masked):
            if count >= 400:
                break
            key = m.group(1)
            if key in ("if", "for", "while", "return", "case", "in", "of",
                       "const", "let", "var", "i", "j", "k"):
                continue
            vs = m.start(2)
            if in_editable(vs):
                continue
            if m.group(3):  # string literal — masked shows quotes, real text in src
                q = m.group(3)
                ve = self.src.find(q, vs + 1)
                while ve != -1 and self.src[ve - 1] == "\\":
                    ve = self.src.find(q, ve + 1)
                if ve == -1:
                    continue
                ve += 1
            else:
                ve = m.end(2)
            raw = self.src[vs:ve]
            ftype, value, readonly, quote = self._classify(raw)
            if readonly:
                continue
            ln = _line_of(self.starts, vs)
            res.fields.append(Field(
                id=self._next_id(), path=f"L{ln + 1}:{key}", key=key,
                value=value, raw=raw, type=ftype, start=vs, end=ve,
                comment=self._trailing_comment(ve),
                section=section_for(vs), quote=quote,
            ))
            count += 1


# ---------------------------------------------------------------------------
# File I/O + patching
# ---------------------------------------------------------------------------

def read_source(path: str | Path) -> str:
    """Bytes → str preserving everything (BOM, CRLF, bad bytes)."""
    data = Path(path).read_bytes()
    return data.decode("utf-8", errors="surrogateescape")


def write_source(path: str | Path, src: str) -> None:
    Path(path).write_bytes(src.encode("utf-8", errors="surrogateescape"))


def parse_file(path: str | Path) -> ParseResult:
    return ScriptParser(read_source(path)).parse()


def apply_edits(src: str, edits: list[dict]) -> str:
    """edits: [{start, end, new_text}] — spliced back-to-front. Overlaps rejected."""
    eds = sorted(edits, key=lambda e: e["start"], reverse=True)
    last_start = len(src) + 1
    for e in eds:
        s, t = int(e["start"]), int(e["end"])
        if not (0 <= s <= t <= len(src)) or t > last_start:
            raise ValueError(f"edit span ทับซ้อน/เกินไฟล์: {s}-{t}")
        last_start = s
        src = src[:s] + str(e["new_text"]) + src[t:]
    return src


def js_string_literal(value: str, quote: str = '"') -> str:
    """Serialize a python str back to a JS string literal with original quote."""
    body = value.replace("\\", "\\\\").replace(quote, "\\" + quote).replace("\n", "\\n")
    return f"{quote}{body}{quote}"
