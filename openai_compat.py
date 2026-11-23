"""Calls to OpenAI-compatible providers (DeepSeek, OpenAI, DeepInfra, Qwen, NVIDIA NIM).

Same request as the old chat-ui's createCompletion(): POST url + path with an
"Authorization: Bearer <key>" header and an OpenAI-style body. The streamed
reply is parsed like its parseChoice(): delta.content is the answer and
delta.reasoning_content (DeepSeek reasoner) is the model's reasoning.
"""

import base64
import io
import json

import requests

from providers import env_key_name as _env_key_name

HINTS = {
    401: "The API key was rejected. Put a valid key in .env as {env_key} and restart.",
    402: "This account has no credit left. Top up your balance on the provider's website, "
         "or pick another provider in the settings.",
    403: "This key isn't allowed to do that yet (for a new xAI team: add credits at console.x.ai), "
         "or pick another provider in the settings.",
    404: "The provider doesn't know this model or URL. Pick another model.",
    429: "Too many requests, or your quota is used up. Wait a minute and try again.",
}


class ProviderError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def env_key_name(provider: dict) -> str:
    return "ANTHROPIC_API_KEY" if provider["kind"] == "anthropic" else _env_key_name(provider["name"])


def _error(provider: dict, resp: requests.Response) -> ProviderError:
    try:
        data = resp.json()
        if isinstance(data, list):  # Gemini wraps the error object in a list
            data = data[0] if data and isinstance(data[0], dict) else {}
        err = data.get("error")
        detail = (err.get("message") if isinstance(err, dict) else err) or data.get("message") or data.get("detail")
    except ValueError:
        detail = None
    message = f"{provider['title']}: {str(detail or resp.reason or resp.text[:300]).strip()}"
    hint = HINTS.get(resp.status_code)
    if hint:
        message += ("" if message.endswith((".", "!", "?")) else ".") + " " + hint.format(env_key=env_key_name(provider))
    return ProviderError(resp.status_code, message)


def _pdf_text(data_b64: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(base64.b64decode(data_b64)))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def to_openai_messages(messages: list[dict]) -> list[dict]:
    """Claude-style content blocks (as the Streamlit app stores them) -> OpenAI format."""
    out = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            out.append({"role": m["role"], "content": content})
            continue
        parts, has_image = [], False
        for block in content:
            kind = block.get("type")
            if kind == "text":
                parts.append({"type": "text", "text": block["text"]})
            elif kind == "image":
                has_image = True
                src = block["source"]
                parts.append({"type": "image_url", "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
            elif kind == "document":
                src, title = block["source"], block.get("title", "document")
                try:
                    text = src["data"] if src.get("type") == "text" else _pdf_text(src["data"])
                except Exception:
                    text = ""
                text = text or "(no readable text; it may be a scanned PDF)"
                parts.append({"type": "text", "text": f"Attached document: {title}\n###\n{text}\n###"})
        if has_image:
            out.append({"role": m["role"], "content": parts})
        else:  # plain string: text-only models (e.g. deepseek-chat) reject content arrays
            out.append({"role": m["role"], "content": "\n\n".join(p["text"] for p in parts)})
    return out


def build_payload(provider: dict, model: str, messages: list[dict], system: str, *, stream: bool,
                  max_tokens=None, temperature=None, top_p=None) -> dict:
    payload = {**provider.get("extra_body", {}),
               "model": model or provider["default_model"],
               "messages": [{"role": "system", "content": system}, *messages],
               "stream": stream}
    max_tokens = str(max_tokens or provider.get("max_tokens_value") or "").strip()
    if max_tokens.isdigit():
        payload[provider["max_tokens_type"]] = int(max_tokens)
    for field, value in (("temperature", temperature), ("top_p", top_p)):
        try:
            if value not in (None, ""):
                payload[field] = float(value)
        except (TypeError, ValueError):
            pass
    return payload


def post(provider: dict, payload: dict) -> requests.Response:
    """Send the request; raises ProviderError for HTTP or connection failures."""
    if provider.get("needs_key", True) and not provider["api_key"]:
        raise ProviderError(401, f"{provider['title']} has no API key. Put it in .env as "
                                 f"{env_key_name(provider)} and restart, or pick another provider.")
    headers = {"Content-Type": "application/json", **provider.get("extra_headers", {})}
    if provider["api_key"]:
        headers["Authorization"] = f"{provider['auth_prefix']} {provider['api_key']}"
    try:
        resp = requests.post(provider["url"], json=payload, headers=headers,
                             stream=payload.get("stream", False), timeout=(15, 600))
    except requests.ConnectionError as exc:
        if "localhost" in provider["url"] or "127.0.0.1" in provider["url"]:
            raise ProviderError(502, f"{provider['title']} isn't running. Start it (for Ollama: open the "
                                     "Ollama app, or run `ollama serve`) and try again.") from exc
        raise ProviderError(502, f"Couldn't reach {provider['title']}. Check your internet connection.") from exc
    except requests.RequestException as exc:
        raise ProviderError(502, f"Couldn't reach {provider['title']}: {exc}") from exc
    if resp.status_code >= 400:
        raise _error(provider, resp)
    return resp


def stream_chat(provider: dict, messages: list[dict], system: str, *, model: str,
                max_tokens=None, temperature=None, top_p=None):
    """Yield ("thinking" | "text", str) while streaming, then ("done", info), like llm.stream_answer()."""
    payload = build_payload(provider, model, messages, system, stream=True,
                            max_tokens=max_tokens, temperature=temperature, top_p=top_p)
    resp = post(provider, payload)
    finish = None
    try:
        for line in resp.iter_lines():
            text = line.decode("utf-8", errors="replace").strip() if line else ""
            if not text.startswith("data:"):
                continue
            data = text[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            for choice in obj.get("choices") or []:
                delta = choice.get("delta") or choice.get("message") or {}
                if delta.get("reasoning_content"):
                    yield "thinking", delta["reasoning_content"]
                if delta.get("content"):
                    yield "text", delta["content"]
                finish = choice.get("finish_reason") or finish
    except requests.RequestException as exc:
        raise ProviderError(502, f"Connection to {provider['title']} dropped: {exc}") from exc
    finally:
        resp.close()
    stop = {"length": "max_tokens", "content_filter": "refusal"}.get(finish, finish)
    yield "done", {"stop_reason": stop, "sources": {}}
