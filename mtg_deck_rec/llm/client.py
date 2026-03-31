"""OpenAI-compatible LLM client with streaming support.

Supports OpenAI, Ollama, and any OpenAI-compatible API.
Configure via environment variables:
  LLM_API_KEY      - API key (not needed for Ollama)
  LLM_BASE_URL     - API base URL (default: https://api.openai.com/v1)
  LLM_MODEL        - Model name (default: gpt-4o-mini)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Generator


def _get_config() -> tuple[str, str, str]:
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    return base_url, api_key, model


def is_configured() -> bool:
    base_url, api_key, _ = _get_config()
    # Ollama doesn't need an API key
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return True
    return bool(api_key)


def chat_stream(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    image_base64: str | None = None,
    image_media_type: str = "image/jpeg",
) -> Generator[str, None, None]:
    """Stream a chat completion, yielding text chunks.

    If image_base64 is provided, sends it as a vision message.
    """
    base_url, api_key, model = _get_config()
    url = f"{base_url}/chat/completions"

    # Build user message content — text only, or multimodal with image
    if image_base64:
        user_content: list | str = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_media_type};base64,{image_base64}",
                },
            },
            {"type": "text", "text": user_prompt},
        ]
        # Vision requests need a vision-capable model
        vision_model = model if "gpt-4o" in model else "gpt-4o-mini"
    else:
        user_content = user_prompt
        vision_model = model

    payload = json.dumps({
        "model": vision_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM API error (HTTP {e.code}): {body}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"Cannot reach LLM API at {base_url}: {e.reason}") from e

    try:
        buffer = ""
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace")
            buffer += line
            while "\n" in buffer:
                event_line, buffer = buffer.split("\n", 1)
                event_line = event_line.strip()
                if not event_line.startswith("data: "):
                    continue
                data_str = event_line[6:]
                if data_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
    finally:
        resp.close()


def chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    image_base64: str | None = None,
    image_media_type: str = "image/jpeg",
) -> str:
    """Non-streaming chat completion (collects full response)."""
    return "".join(chat_stream(
        system_prompt, user_prompt, temperature, max_tokens,
        image_base64=image_base64, image_media_type=image_media_type,
    ))


class LLMError(Exception):
    pass
