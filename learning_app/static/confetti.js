// Tiny CSS-animation confetti burst — no library, no canvas
(() => {
  const COLORS = ["#635bff", "#00d179", "#ffb84d", "#ff5c5c", "#8b83ff"];
  const PIECES = 60;
  const DURATION = 2600;

  function burst() {
    const wrap = document.createElement("div");
    wrap.className = "confetti-wrap";
    wrap.setAttribute("aria-hidden", "true");
    document.body.appendChild(wrap);

    for (let i = 0; i < PIECES; i++) {
      const p = document.createElement("span");
      p.className = "confetti-piece";
      p.style.left = `${Math.random() * 100}%`;
      p.style.background = COLORS[i % COLORS.length];
      p.style.animationDelay = `${Math.random() * 300}ms`;
      p.style.animationDuration = `${1600 + Math.random() * 800}ms`;
      p.style.transform = `rotate(${Math.random() * 360}deg)`;
      wrap.appendChild(p);
    }

    setTimeout(() => wrap.remove(), DURATION);
  }

  // Only fire if the page was rendered with ?completed=1
  const params = new URLSearchParams(window.location.search);
  if (params.get("completed") === "1") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", burst);
    } else {
      burst();
    }
  }
})();
