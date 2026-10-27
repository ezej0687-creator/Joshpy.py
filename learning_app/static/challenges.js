// Auto-graded exercise UI. Talks to the existing Pyodide iframe.
(() => {
  const container = document.querySelector("[data-challenges]");
  const runnerFrame = document.querySelector(".python-runner-frame");
  if (!container || !runnerFrame) return;

  const lessonId = parseInt(container.dataset.challenges, 10);
  if (!lessonId) return;

  let exercises = [];
  let currentIndex = 0;
  let pendingRequest = null;

  const listEl = container.querySelector("[data-exercise-list]");
  const titleEl = container.querySelector("[data-ex-title]");
  const promptEl = container.querySelector("[data-ex-prompt]");
  const statusEl = container.querySelector("[data-ex-status]");
  const hintBtn = container.querySelector("[data-ex-hint]");
  const hintEl = container.querySelector("[data-ex-hint-text]");
  const resultsEl = container.querySelector("[data-ex-results]");
  const runTestsBtn = container.querySelector("[data-run-tests]");

  function loadExercises() {
    fetch(`/api/exercises/${lessonId}`, { credentials: "same-origin" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        exercises = data.exercises || [];
        if (!exercises.length) {
          listEl.innerHTML = '<p class="empty-state">No auto-graded exercises for this lesson.</p>';
          titleEl.textContent = "";
          promptEl.textContent = "";
          runTestsBtn.hidden = true;
          return;
        }
        const first = exercises.findIndex((e) => e.unlocked && !e.passed);
        currentIndex = first >= 0 ? first : 0;
        renderList();
        renderExercise();
        runTestsBtn.hidden = false;
      })
      .catch((err) => {
        listEl.innerHTML = `<p class="empty-state">Could not load exercises: ${escapeHtml(err.message)}</p>`;
      });
  }

  function renderList() {
    listEl.innerHTML = "";
    exercises.forEach((ex, i) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "ex-list-item";
      if (ex.passed) row.classList.add("ex-passed");
      if (i === currentIndex) row.classList.add("ex-active");
      if (!ex.unlocked) {
        row.classList.add("ex-locked");
        row.disabled = true;
        row.innerHTML = `<span class="ex-icon">🔒</span><span>${i + 1}. ${escapeHtml(ex.title)}</span>`;
      } else {
        const icon = ex.passed ? "✓" : i === currentIndex ? "●" : "○";
        row.innerHTML = `<span class="ex-icon">${icon}</span><span>${i + 1}. ${escapeHtml(ex.title)}</span>`;
        row.addEventListener("click", () => {
          currentIndex = i;
          renderList();
          renderExercise();
        });
      }
      listEl.appendChild(row);
    });
  }

  function renderExercise() {
    const ex = exercises[currentIndex];
    if (!ex) return;
    titleEl.textContent = `Exercise ${currentIndex + 1} — ${ex.title}`;
    promptEl.textContent = ex.prompt || "";
    resultsEl.innerHTML = "";

    if (ex.hint) {
      hintBtn.hidden = false;
      hintEl.textContent = ex.hint;
      hintEl.hidden = true;
    } else {
      hintBtn.hidden = true;
      hintEl.hidden = true;
    }

    // Load starter code into the practice editor
    const practiceBlock = document.querySelector("[data-practice-editor]");
    if (practiceBlock) {
      if (practiceBlock.editor) {
        practiceBlock.editor.setValue(ex.starter_code || "");
      } else {
        const ta = practiceBlock.querySelector("textarea");
        if (ta) ta.value = ex.starter_code || "";
      }
    }

    runTestsBtn.disabled = !ex.unlocked;
    updateStatus();
  }

  function updateStatus() {
    const ex = exercises[currentIndex];
    if (!ex) return;
    const total = ex.tests.length;
    statusEl.textContent = ex.passed
      ? `All ${total} test${total === 1 ? "" : "s"} passed ✓`
      : `${total} test${total === 1 ? "" : "s"} to pass`;
  }

  function getCurrentCode() {
    const practiceBlock = document.querySelector("[data-practice-editor]");
    if (!practiceBlock) return "";
    if (practiceBlock.editor) return practiceBlock.editor.getValue();
    const ta = practiceBlock.querySelector("textarea");
    return ta ? ta.value : "";
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  window.addEventListener("message", (event) => {
    if (event.source !== runnerFrame.contentWindow) return;
    const msg = event.data;
    if (!msg || msg.type !== "test-result" || msg.requestId !== pendingRequest) return;

    pendingRequest = null;
    runTestsBtn.disabled = false;
    runTestsBtn.textContent = "Run tests";
    renderResults(msg.results || []);

    const ex = exercises[currentIndex];
    const allPassed = msg.results.length > 0 && msg.results.every((r) => r.passed);
    if (allPassed) {
      fetch(`/api/exercise-complete/${ex.id}`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRF-Token": container.dataset.csrf || "" },
      })
        .then(() => {
          ex.passed = true;
          const nextIdx = currentIndex + 1;
          if (nextIdx < exercises.length) exercises[nextIdx].unlocked = true;
          renderList();
          updateStatus();
          // Small delay before advancing so the user sees the green checks
          if (nextIdx < exercises.length) {
            setTimeout(() => {
              currentIndex = nextIdx;
              renderList();
              renderExercise();
            }, 1200);
          }
        })
        .catch(() => {});
    }
  });

  function renderResults(results) {
    resultsEl.innerHTML = "";
    results.forEach((r) => {
      const row = document.createElement("div");
      row.className = `ex-result ${r.passed ? "ex-pass" : "ex-fail"}`;
      if (r.error) {
        row.innerHTML = `<span class="ex-result-icon">✗</span><span><code>${escapeHtml(r.name)}</code> — <em>error:</em> ${escapeHtml(r.error)}</span>`;
      } else if (r.passed) {
        row.innerHTML = `<span class="ex-result-icon">✓</span><span><code>${escapeHtml(r.name)}</code></span>`;
      } else {
        row.innerHTML = `<span class="ex-result-icon">✗</span><span><code>${escapeHtml(r.name)}</code> → expected <strong>${escapeHtml(r.expected)}</strong>, got <strong>${escapeHtml(r.actual)}</strong></span>`;
      }
      resultsEl.appendChild(row);
    });
    const total = results.length;
    const passed = results.filter((r) => r.passed).length;
    const summary = document.createElement("p");
    summary.className = "ex-summary";
    summary.textContent = `${passed} of ${total} test${total === 1 ? "" : "s"} passed`;
    resultsEl.appendChild(summary);
  }

  runTestsBtn.addEventListener("click", () => {
    const ex = exercises[currentIndex];
    if (!ex || pendingRequest) return;
    const code = getCurrentCode();
    if (!code.trim()) {
      resultsEl.innerHTML = '<p class="ex-summary">Write some code before running tests.</p>';
      return;
    }
    pendingRequest = `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    runTestsBtn.disabled = true;
    runTestsBtn.textContent = "Running...";
    resultsEl.innerHTML = "";
    runnerFrame.contentWindow.postMessage({
      type: "test",
      requestId: pendingRequest,
      code,
      tests: ex.tests,
    }, "*");
  });

  hintBtn.addEventListener("click", () => {
    hintEl.hidden = !hintEl.hidden;
  });

  loadExercises();
})();
