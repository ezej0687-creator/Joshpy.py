(() => {
  const practiceBlocks = Array.from(
    document.querySelectorAll("[data-practice-editor]")
  );
  const runnerFrame = document.querySelector(".python-runner-frame");

  if (!practiceBlocks.length || !runnerFrame) {
    return;
  }

  let nextRequestId = 0;
  let runnerReady = false;
  let pingIntervalId;
  const pendingRuns = new Map();

  function waitForRunner() {
    runnerReady = false;
    window.clearInterval(pingIntervalId);
    const ping = () => {
      runnerFrame.contentWindow.postMessage({ type: "ping" }, "*");
    };
    ping();
    pingIntervalId = window.setInterval(ping, 250);
  }

  function sendRun(requestId, run) {
    if (!runnerReady || run.sent) {
      return;
    }
    run.sent = true;
    runnerFrame.contentWindow.postMessage({
      type: "run",
      requestId,
      code: run.code,
      input: run.input,
    }, "*");
  }

  function setStatus(block, message) {
    block.querySelector("[data-editor-status]").textContent = message;
  }

  function getCode(block) {
    return block.editor ? block.editor.getValue() : block.querySelector("textarea").value;
  }

  function setCode(block, code) {
    if (block.editor) {
      block.editor.setValue(code);
    } else {
      block.querySelector("textarea").value = code;
    }
  }

  function showOutput(block, text, isError) {
    const output = block.querySelector("[data-python-output]");
    output.textContent = text || (isError ? "Python stopped without a result." : "Code ran successfully with no output.");
    output.classList.toggle("is-error", isError);
    output.hidden = false;
  }

  function cancelRun(block, button, requestId) {
    const run = pendingRuns.get(requestId);
    if (!run) {
      return;
    }
    clearTimeout(run.timeoutId);
    pendingRuns.delete(requestId);
    button.disabled = false;
    button.textContent = "Run Python";
    setStatus(block, "Execution stopped. The browser runtime is restarting.");
    showOutput(block, "Execution stopped.", true);
    runnerFrame.src = runnerFrame.src;
    waitForRunner();
  }

  window.addEventListener("message", (event) => {
    if (event.source !== runnerFrame.contentWindow || !event.data) {
      return;
    }
    const message = event.data;
    if (message.type === "ready") {
      runnerReady = true;
      window.clearInterval(pingIntervalId);
      for (const [requestId, run] of pendingRuns) {
        sendRun(requestId, run);
      }
      return;
    }
    const run = pendingRuns.get(message.requestId);
    if (!run) {
      return;
    }

    if (message.type === "status") {
      if (message.status === "loading") {
        setStatus(run.block, "Loading Python in your browser. The first run may take a moment.");
      } else if (message.status === "running") {
        clearTimeout(run.timeoutId);
        setStatus(run.block, "Running in your browser. Select Stop if it takes too long.");
        run.timeoutId = window.setTimeout(() => {
          cancelRun(run.block, run.button, message.requestId);
          setStatus(run.block, "Stopped after 10 seconds to keep the page responsive.");
        }, 10000);
      }
      return;
    }

    if (message.type === "result") {
      clearTimeout(run.timeoutId);
      pendingRuns.delete(message.requestId);
      run.button.disabled = false;
      run.button.textContent = "Run Python";
      setStatus(run.block, message.isError ? "Python reported an error." : "Run complete.");
      showOutput(run.block, message.output, message.isError);
    }
  });

  for (const block of practiceBlocks) {
    const textarea = block.querySelector("textarea");
    const inputArea = block.querySelector("[data-program-input]");
    const storageKey = block.dataset.storageKey;
    const inputStorageKey = `${storageKey}-input`;

    try {
      const savedDraft = window.localStorage.getItem(storageKey);
      const savedInput = window.localStorage.getItem(inputStorageKey);
      if (savedDraft !== null) {
        textarea.value = savedDraft;
        setStatus(block, "Saved draft restored from this browser.");
      }
      if (savedInput !== null) {
        inputArea.value = savedInput;
      }
    } catch (_error) {
      setStatus(block, "Draft storage is unavailable in this browser.");
    }

    if (window.CodeMirror) {
      block.editor = window.CodeMirror.fromTextArea(textarea, {
        mode: "python",
        lineNumbers: true,
        indentUnit: 4,
        tabSize: 4,
        indentWithTabs: false,
        lineWrapping: false,
        placeholder: "# Write your Python solution here",
      });
      block.editor.setSize(null, 190);
      block.editor.on("change", () => {
        try {
          window.localStorage.setItem(storageKey, block.editor.getValue());
          setStatus(block, "Draft saved in this browser.");
        } catch (_error) {
          setStatus(block, "Could not save the draft. Browser storage may be full or disabled.");
        }
      });
    } else {
      textarea.addEventListener("input", () => {
        try {
          window.localStorage.setItem(storageKey, textarea.value);
          setStatus(block, "Draft saved in this browser. Syntax highlighting did not load.");
        } catch (_error) {
          setStatus(block, "Could not save the draft. Browser storage may be full or disabled.");
        }
      });
    }

    inputArea.addEventListener("input", () => {
      try {
        window.localStorage.setItem(inputStorageKey, inputArea.value);
        setStatus(block, "Code and program input saved in this browser.");
      } catch (_error) {
        setStatus(block, "Could not save the draft. Browser storage may be full or disabled.");
      }
    });

    block.querySelector("[data-run-python]").addEventListener("click", (event) => {
      const button = event.currentTarget;
      const activeRun = Array.from(pendingRuns.entries()).find(
        ([, run]) => run.block === block
      );
      if (activeRun) {
        cancelRun(block, button, activeRun[0]);
        return;
      }
      if (pendingRuns.size) {
        setStatus(block, "Wait for the current Python run to finish.");
        return;
      }

      const code = getCode(block);
      if (!code.trim()) {
        setStatus(block, "Write some Python code before running this exercise.");
        return;
      }

      const requestId = `practice-${Date.now()}-${nextRequestId++}`;
      const timeoutId = window.setTimeout(() => {
        const run = pendingRuns.get(requestId);
        if (run) {
          pendingRuns.delete(requestId);
          run.button.disabled = false;
          run.button.textContent = "Run Python";
          setStatus(run.block, "The browser Python runtime did not respond. Check your connection and try again.");
          showOutput(run.block, "The runtime did not respond.", true);
          runnerFrame.src = runnerFrame.src;
          waitForRunner();
        }
      }, 90000);

      const run = {
        block,
        button,
        timeoutId,
        code,
        input: inputArea.value,
        sent: false,
      };
      pendingRuns.set(requestId, run);
      button.textContent = "Stop";
      setStatus(block, "Starting the browser Python runtime...");
      const output = block.querySelector("[data-python-output]");
      output.hidden = true;
      sendRun(requestId, run);
    });

    block.querySelector("[data-download-python]").addEventListener("click", () => {
      const code = getCode(block);
      if (!code.trim()) {
        setStatus(block, "Write some Python code before downloading it.");
        return;
      }
      const blob = new Blob([code], { type: "text/x-python;charset=utf-8" });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `lesson-${block.dataset.lessonId}-exercise-${block.dataset.exerciseNumber}.py`;
      link.click();
      URL.revokeObjectURL(downloadUrl);
      setStatus(block, "Python file downloaded.");
    });

    block.querySelector("[data-clear-draft]").addEventListener("click", () => {
      try {
        window.localStorage.removeItem(storageKey);
        window.localStorage.removeItem(inputStorageKey);
      } catch (_error) {
        setStatus(block, "Could not clear the saved draft in this browser.");
        return;
      }
      setCode(block, "");
      inputArea.value = "";
      block.querySelector("[data-python-output]").hidden = true;
      setStatus(block, "Draft cleared.");
    });
  }

  waitForRunner();
})();
