import json
import requests
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


class OllamaError(RuntimeError):
    pass


def chat(messages, *, json_mode=False, temperature=0.1):
    """Call Ollama with Qwen3 thinking disabled."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature
        }
    }
    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        content = (data.get("message") or {}).get("content", "")
        if not content:
            raise OllamaError("Ollama returned an empty message.")
        return content
    except requests.RequestException as exc:
        raise OllamaError(
            f"Could not reach Ollama at {OLLAMA_BASE_URL}: {exc}"
        ) from exc


def extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise OllamaError("Qwen did not return valid JSON.")
