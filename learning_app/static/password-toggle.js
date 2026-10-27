// Adds a show/hide toggle to every <input type="password"> on the page.
(() => {
  const EYE_OPEN = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>`;
  const EYE_CLOSED = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a20.3 20.3 0 0 1 5.06-6.06"/>
      <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a20.3 20.3 0 0 1-3.16 4.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>`;

  function enhance(input) {
    if (input.dataset.passwordEnhanced === "1") return;
    if (input.type !== "password") return;
    input.dataset.passwordEnhanced = "1";

    const wrapper = document.createElement("span");
    wrapper.className = "password-field";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "password-toggle";
    btn.setAttribute("aria-label", "Show password");
    btn.setAttribute("aria-pressed", "false");
    btn.innerHTML = EYE_OPEN;
    wrapper.appendChild(btn);

    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.innerHTML = showing ? EYE_OPEN : EYE_CLOSED;
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      btn.setAttribute("aria-pressed", showing ? "false" : "true");
      input.focus();
    });
  }

  function enhanceAll(root = document) {
    root.querySelectorAll('input[type="password"]').forEach(enhance);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => enhanceAll());
  } else {
    enhanceAll();
  }
})();
