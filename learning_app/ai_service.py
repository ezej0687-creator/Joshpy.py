import json
import os
from urllib.request import Request, urlopen

def stream_tutor_reply(messages):
    """Yields text chunks from the Groq API."""
    provider = os.environ.get("AI_PROVIDER", "groq").lower()
    
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        base_url = "https://api.groq.com/openai/v1/chat/completions"
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = "https://api.openai.com/v1/chat/completions"
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.5,
        "max_tokens": 800,
    }).encode("utf-8")

    req = Request(
        base_url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Python-Learning-Tutor/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        chunk = data["choices"][0]["delta"].get("content", "")
                        if chunk:
                            yield chunk
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except Exception as e:
        yield f"\n[Error: {str(e)}]"
