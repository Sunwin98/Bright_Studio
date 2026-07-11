import { el } from "./api.js";
import { playClick } from "./sound.js";

const quotes = [
  "ยินดีต้อนรับสู่ Bright Studio!",
  "สร้าง Addon สนุกๆ กันเถอะ",
  "ฉันช่วยอะไรได้บ้าง?",
  "อย่าลืมพักสายตาบ้างนะ~",
  "รอโหลดแป๊บนึงนะ"
];

let state = "idle";
const imgPaths = {
  idle: "/assets/mascot_idle.png",
  happy: "/assets/mascot_happy.png",
  angry: "/assets/mascot_angry.png"
};

export function createMascot() {
  const img = el("img", { src: imgPaths[state], class: "mascot-img", style: "width: 140px; height: auto;" });
  const bubble = el("div", { class: "mascot-bubble" });
  bubble.style.display = "none";
  
  const container = el("div", { class: "mascot-container" }, img, bubble);
  document.body.append(container);
  
  let isDragging = false;
  let offsetX = 0, offsetY = 0;
  let moved = false;
  
  img.addEventListener("mousedown", (e) => {
    isDragging = true;
    moved = false;
    offsetX = e.clientX - container.getBoundingClientRect().left;
    offsetY = e.clientY - container.getBoundingClientRect().top;
    img.style.cursor = "grabbing";
  });
  
  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    moved = true;
    container.style.left = (e.clientX - offsetX) + "px";
    container.style.top = (e.clientY - offsetY) + "px";
    container.style.right = "auto";
    container.style.bottom = "auto";
  });
  
  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      img.style.cursor = "grab";
    }
  });

  img.addEventListener("click", () => {
    if (moved) return;
    playClick();
    const text = quotes[Math.floor(Math.random() * quotes.length)];
    bubble.textContent = text;
    bubble.style.display = "block";
    setState("happy");
    setTimeout(() => {
      bubble.style.display = "none";
      setState("idle");
    }, 3000);
  });
}

export function setState(newState) {
  state = newState;
  const img = document.querySelector(".mascot-img");
  if (img) img.src = imgPaths[state];
}
