(() => {
  const chat = document.querySelector("[data-tutor-chat]");
  const form = chat?.querySelector("[data-chat-form]");
  const input = chat?.querySelector("[data-chat-input]");
  const messagesElement = chat?.querySelector("[data-chat-messages]");
  const status = chat?.querySelector("[data-chat-status]");
  const sendButton = chat?.querySelector("[data-send-chat]");
  const clearButton = chat?.querySelector("[data-clear-chat]");
  if (!chat || !form || !input || !messagesElement || !status || !sendButton) return;

  let messages = [];

  function appendMessage(role, content, className = "") {
    const bubble = document.createElement("article");
    bubble.className = `chat-message chat-message-${role}${className ? ` ${className}` : ""}`;
    bubble.setAttribute("aria-label", role === "user" ? "Your message" : "Tutor reply");
    bubble.textContent = content;

    const nearBottom =
      messagesElement.scrollHeight - messagesElement.scrollTop - messagesElement.clientHeight < 100;

    messagesElement.append(bubble);
    if (nearBottom || role === "user") {
      messagesElement.scrollTop = messagesElement.scrollHeight;
    }
  }

  function resetConversation() {
    messages = [];
    messagesElement.replaceChildren();
    const welcome = document.createElement("p");
    welcome.className = "tutor-welcome";
    welcome.textContent = "What Python topic or exercise would you like help with? I’ll guide you with hints and clear steps.";
    messagesElement.append(welcome);
    status.textContent = "Conversation cleared. Ask a new question.";
    input.focus();
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || sendButton.disabled) return;

    appendMessage("user", question);
    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;
    status.textContent = "The tutor is thinking…";

    const requestMessages = [
      ...messages.slice(-10),
      { role: "user", content: question },
    ];
    try {
      const response = await fetch("/api/tutor", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": chat.dataset.csrf,
        },
        body: JSON.stringify({
          messages: requestMessages,
          lesson_id: chat.dataset.lessonId || null,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "The tutor could not reply.");

      appendMessage("assistant", result.reply);
      messages = [...requestMessages, { role: "assistant", content: result.reply }].slice(-12);
      status.textContent = "You can ask a follow-up or start a new conversation.";
    } catch (error) {
      appendMessage("assistant", error.message || "The tutor could not reply.", "chat-message-error");
      input.value = question;
      status.textContent = "Your question was not saved to the conversation. Please try again.";
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  clearButton?.addEventListener("click", resetConversation);
})();
