"""Knowledge base API — list and read the markdown skill docs.

Only files that live under one of config.KNOWLEDGE_DIRS may be read, so a crafted
`path` can't escape into the rest of the disk.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

import config

router = APIRouter(prefix="/api", tags=["knowledge"])


def _allowed_roots() -> list[Path]:
    return [d.resolve() for d in config.KNOWLEDGE_DIRS if d.exists()]


def _is_allowed(target: Path) -> bool:
    target = target.resolve()
    for root in _allowed_roots():
        try:
            target.relative_to(root)
            return True
        except ValueError:
            continue
    return False


@router.get("/knowledge")
def list_docs():
    docs = []
    seen = set()
    for root in _allowed_roots():
        for md in sorted(root.glob("*.md")):
            key = str(md.resolve())
            if key in seen:
                continue
            seen.add(key)
            try:
                mtime = md.stat().st_mtime
            except OSError:
                mtime = 0.0
            docs.append({
                "title": md.stem,
                "path": str(md),
                "group": root.name,
                "mtime": mtime,
            })
    return {"docs": docs}


@router.get("/knowledge/search")
def search_docs(q: str):
    """Case-insensitive full-text search across every doc. Returns per-doc
    match count + a snippet around the first hit."""
    needle = q.strip().lower()
    if len(needle) < 2:
        raise HTTPException(status_code=400, detail="คำค้นสั้นเกินไป (อย่างน้อย 2 ตัวอักษร)")
    results = []
    seen = set()
    for root in _allowed_roots():
        for md in sorted(root.glob("*.md")):
            key = str(md.resolve())
            if key in seen:
                continue
            seen.add(key)
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            low = text.lower()
            count = low.count(needle)
            if not count:
                continue
            i = low.find(needle)
            snip_start = max(0, i - 60)
            snippet = text[snip_start:i + len(needle) + 90].replace("\n", " ").strip()
            results.append({
                "title": md.stem,
                "path": str(md),
                "group": root.name,
                "count": count,
                "snippet": ("…" if snip_start else "") + snippet + "…",
            })
    results.sort(key=lambda r: r["count"], reverse=True)
    return {"query": q, "results": results[:40]}


@router.get("/knowledge/doc")
def read_doc(path: str):
    p = Path(path)
    if not p.exists() or not _is_allowed(p):
        raise HTTPException(status_code=404, detail="ไม่พบเอกสาร หรือไม่มีสิทธิ์เข้าถึง")
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"title": p.stem, "markdown": text}
