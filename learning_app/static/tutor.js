(() => {
  const chat = document.querySelector("[data-tutor-chat]");
  const form = chat?.querySelector("[data-chat-form]");
  const input = chat?.querySelector("[data-chat-input]");
  const messagesElement = chat?.querySelector("[data-chat-messages]");
  const status = chat?.querySelector("[data-chat-status]");
  const sendButton = chat?.querySelector("[data-send-chat]");
  if (!chat || !form || !input || !messagesElement || !status || !sendButton) return;

  let messages = [];

  function appendMessage(role, content, className = "") {
    const bubble = document.createElement("article");
    bubble.className = `chat-message chat-message-${role}${className ? ` ${className}` : ""}`;
    bubble.setAttribute("aria-label", role === "user" ? "Your message" : "Tutor reply");
    bubble.textContent = content;
    messagesElement.append(bubble);
    messagesElement.scrollTop = messagesElement.scrollHeight;
    return bubble;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || sendButton.disabled) return;

    appendMessage("user", question);
    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;
    status.textContent = "The tutor is typing…";

    const requestMessages = [
      ...messages.slice(-10),
      { role: "user", content: question },
    ];

    const assistantBubble = appendMessage("assistant", "");
    
    try {
      const response = await fetch("/api/tutor/stream", {
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

      if (!response.ok) throw new Error("Stream failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullReply = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        fullReply += chunk;
        assistantBubble.textContent = fullReply;
        messagesElement.scrollTop = messagesElement.scrollHeight;
      }

      messages = [...requestMessages, { role: "assistant", content: fullReply }].slice(-12);
      status.textContent = "You can ask a follow-up.";

    } catch (error) {
      assistantBubble.textContent = "Something went wrong. Please try again.";
      assistantBubble.classList.add("chat-message-error");
      status.textContent = "Your question was not saved. Please try again.";
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
})();
