(() => {
  const chat = document.querySelector("[data-tutor-chat]");
  const form = chat?.querySelector("[data-chat-form]");
  const input = chat?.querySelector("[data-chat-input]");
  const messagesElement = chat?.querySelector("[data-chat-messages]");
  const status = chat?.querySelector("[data-chat-status]");
  const sendButton = chat?.querySelector("[data-send-chat]");
  if (!chat || !form || !input || !messagesElement || !status || !sendButton) return;

  let messages = [];

  // Configure marked for syntax highlighting (optional, but nice)
  marked.setOptions({
    breaks: true,
    gfm: true
  });

  function appendMessage(role, content, className = "") {
    const wrapper = document.createElement("div");
    wrapper.className = "flex items-start gap-3 " + (role === "user" ? "flex-row-reverse" : "");

    // Avatar
    const avatar = document.createElement("div");
    avatar.className = `w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${role === 'user' ? 'bg-gray-200' : 'bg-brand-100'}`;
    avatar.innerHTML = role === 'user' 
      ? '<svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>'
      : '<svg class="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>';

    // Bubble
    const bubble = document.createElement("div");
    bubble.className = `px-4 py-3 rounded-2xl shadow-sm border text-sm leading-relaxed max-w-[85%] overflow-x-auto ${
      role === "user" 
        ? "bg-brand-600 text-white rounded-tr-sm border-transparent" 
        : "bg-white text-gray-800 rounded-tl-sm border-gray-100"
    } ${className}`;
    
    if (role === "user") {
      bubble.textContent = content; // User text is plain
    } else {
      bubble.innerHTML = marked.parse(content); // AI text is Markdown
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesElement.appendChild(wrapper);
    messagesElement.scrollTop = messagesElement.scrollHeight;
    
    return bubble;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || sendButton.disabled) return;

    appendMessage("user", question);
    input.value = "";
    input.style.height = "44px";
    input.disabled = true;
    sendButton.disabled = true;
    status.textContent = "The tutor is thinking…";

    const requestMessages = [
      ...messages.slice(-10),
      { role: "user", content: question },
    ];

    // Create the assistant bubble early with a loading dots animation
    const assistantBubble = appendMessage("assistant", "");
    assistantBubble.innerHTML = '<span class="flex gap-1 items-center h-5"><span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span><span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.15s"></span><span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.3s"></span></span>';
    
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
        // Parse markdown in real-time as it streams
        assistantBubble.innerHTML = marked.parse(fullReply);
        messagesElement.scrollTop = messagesElement.scrollHeight;
      }

      messages = [...requestMessages, { role: "assistant", content: fullReply }].slice(-12);
      status.textContent = "AI can make mistakes. Verify important info.";

    } catch (error) {
      assistantBubble.innerHTML = "<span class='text-red-500'>Something went wrong. Please try again.</span>";
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
