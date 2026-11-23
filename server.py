"""Backend and web server for Constitution Ai.

Serves the website (website/, built from the Aigocy template) at /, the chat
dashboard (static/index.html) at /app, and the old chat-ui page at /classic.

Chat requests work like the old chat-ui's backend: the page posts an OpenAI-style chat
request, and the server forwards it to the chosen provider (DeepSeek, OpenAI,
DeepInfra, Qwen, NVIDIA NIM... from ./providers, or Anthropic Claude). Before
forwarding, it adds the legal system prompt and, if the user picked any, the
most relevant passages from their reference datasets in ./datasets.

API keys stay on the server (.env or the provider JSON files) and never reach
the browser.

Run with:  python server.py   then open http://localhost:8000
"""

import io
import itertools
import json
import os
import re

import anthropic
import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

import dataset
import llm
import openai_compat
import providers
from attachments import extract_text
from prompts import build_system_prompt
from website.routes import bp as website_bp, not_found_page

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE, override=True)


def reload_env() -> None:
    """Re-read .env so a new or changed API key works without restarting the server."""
    load_dotenv(ENV_FILE, override=True)

EFFORTS = {"low", "medium", "high", "max"}
DATA_URL = re.compile(r"^data:(image/[\w.+-]+);base64,(.+)$", re.DOTALL)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # uploads and image-bearing chats


def error_response(status: int, message: str):
    # Same shape as OpenAI errors; the page shows error.message in its snackbar.
    return jsonify({"error": {"message": message}}), status


def chunk(delta: dict) -> str:
    return f"data: {json.dumps({'choices': [{'delta': delta}]})}\n\n"


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(item.get("text", "") for item in content or [] if item.get("type") == "text")


def split_messages(raw: list[dict]) -> tuple[str, list[dict]]:
    """Separate the page's prompt-card "system" message from the conversation.

    Keeps user and assistant turns (dropping reasoning_content and empty
    tool_calls, as the old createCompletion() did), skips MCP tool messages,
    and makes sure the conversation starts and ends with the user.
    """
    instructions, messages = [], []
    for m in raw:
        role, content = m.get("role"), m.get("content")
        if role == "system":
            instructions.append(text_of(content))
        elif role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content if role == "user" else text_of(content)})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    while messages and messages[-1]["role"] != "user":
        messages.pop()
    return "\n\n".join(i for i in instructions if i.strip()), messages


def retrieval_query(messages: list[dict]) -> str:
    """The last two user turns, so short follow-ups still find the right passages."""
    users = [text_of(m["content"]) for m in messages if m["role"] == "user"]
    return " ".join(users[-2:])


def passages_note(passages: list[dict]) -> str:
    if not passages:
        return ""
    used = ", ".join(f"{p['dataset']} #{p['chunk']}" for p in passages)
    return f"\n\n_Reference passages used: {used}_"


# ---- Claude ---------------------------------------------------------------

def to_claude_content(content):
    if isinstance(content, str):
        return content
    blocks = []
    for item in content:
        if item.get("type") == "text" and item.get("text"):
            blocks.append({"type": "text", "text": item["text"]})
        elif item.get("type") == "image_url":
            match = DATA_URL.match(item.get("image_url", {}).get("url", ""))
            if match:
                blocks.append({"type": "image", "source": {"type": "base64", "media_type": match[1], "data": match[2]}})
    return blocks


def claude_error(exc: Exception) -> str:
    if isinstance(exc, anthropic.AuthenticationError):
        return "Claude rejected the API key. Check ANTHROPIC_API_KEY in your .env file."
    if isinstance(exc, anthropic.RateLimitError):
        return "Claude: too many requests right now. Wait a minute and try again."
    if isinstance(exc, anthropic.APIStatusError):
        if "credit balance" in str(exc.message).lower():
            return ("Your Anthropic account has no credit left. Add credits at console.anthropic.com → "
                    "Plans & Billing, or pick a free provider (Groq, Gemini, OpenRouter).")
        return f"Claude API error ({exc.status_code}): {exc.message}"
    if isinstance(exc, anthropic.APIConnectionError):
        return "Couldn't reach the Claude API. Check your internet connection."
    return f"Unexpected error: {exc}"


def call_claude(provider: dict, body: dict, system: str, messages: list[dict], notes: str):
    model = body.get("model") if body.get("model") in provider["models"] else provider["default_model"]
    web_search = bool(body.get("web_search"))
    claude_messages = [{"role": m["role"], "content": to_claude_content(m["content"])} for m in messages]
    events = llm.stream_answer(
        anthropic.Anthropic(api_key=provider["api_key"]), claude_messages, system,
        model=model,
        effort=body.get("effort") if body.get("effort") in EFFORTS else "high",
        show_thinking=bool(body.get("show_reasoning", True)),
        web_search=web_search,
    )
    # Wait for the first event so an API error becomes an HTTP error the page shows.
    try:
        events = itertools.chain([next(events)], events)
    except anthropic.APIStatusError as exc:
        return error_response(exc.status_code, claude_error(exc))
    except anthropic.APIError as exc:
        return error_response(502, claude_error(exc))

    def closing(info: dict) -> str:
        extra = ""
        if info.get("sources"):
            extra += "\n\n**Sources**\n" + "\n".join(f"- [{t}]({u})" for u, t in info["sources"].items())
        if info.get("stop_reason") == "refusal":
            extra += "\n\n_I can't help with that request. Please rephrase it or ask a lawyer directly._"
        elif info.get("stop_reason") == "max_tokens":
            extra += "\n\n_(The answer was cut off because it was too long. Ask me to continue.)_"
        return extra + notes

    if not body.get("stream", True):
        content, reasoning = "", ""
        try:
            for kind, value in events:
                if kind == "text":
                    content += value
                elif kind == "thinking":
                    reasoning += value
                elif kind == "done":
                    content += closing(value)
        except anthropic.APIError as exc:
            return error_response(502, claude_error(exc))
        return jsonify({"choices": [{"message": {"role": "assistant", "content": content,
                                                 "reasoning_content": reasoning}}]})

    def sse():
        try:
            for kind, value in events:
                if kind == "text":
                    yield chunk({"content": value})
                elif kind == "thinking":
                    yield chunk({"reasoning_content": value})
                elif kind == "status":
                    yield chunk({"reasoning_content": f"\n[{value}]\n"})
                elif kind == "done" and (extra := closing(value)):
                    yield chunk({"content": extra})
        except anthropic.APIError as exc:
            yield chunk({"content": f"\n\n**Error:** {claude_error(exc)}"})
        yield "data: [DONE]\n\n"

    return Response(sse(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---- OpenAI-compatible providers (the old chat-ui's backends) -------------

def call_openai_compatible(provider: dict, body: dict, system: str, messages: list[dict], notes: str):
    stream = bool(body.get("stream", True))
    payload = openai_compat.build_payload(
        provider, body.get("model"), messages, system, stream=stream,
        max_tokens=body.get("max_tokens_value"), temperature=body.get("temperature"), top_p=body.get("top_p"),
    )
    try:
        resp = openai_compat.post(provider, payload)
    except openai_compat.ProviderError as exc:
        return error_response(exc.status, exc.message)

    if not stream:
        data = resp.json()
        try:
            data["choices"][0]["message"]["content"] = (data["choices"][0]["message"].get("content") or "") + notes
        except (KeyError, IndexError, TypeError):
            pass
        return jsonify(data)

    def relay():
        # Pass the provider's server-sent events straight through: the page
        # already parses this format. Add the dataset note just before [DONE].
        done = False
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace")
                if text.strip() == "data: [DONE]":
                    if notes:
                        yield chunk({"content": notes})
                    done = True
                yield text + "\n\n"
            if not done:
                if notes:
                    yield chunk({"content": notes})
                yield "data: [DONE]\n\n"
        except requests.RequestException as exc:
            yield chunk({"content": f"\n\n**Error:** connection to {provider['title']} dropped ({exc})"})
        finally:
            resp.close()  # also runs when the page presses Stop and disconnects

    return Response(relay(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---- Routes ---------------------------------------------------------------

@app.get("/app")
def dashboard():
    """The chat dashboard (static/index.html). The website home page is at /."""
    return send_from_directory(app.static_folder, "index.html")


app.register_blueprint(website_bp)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith(("/api/", "/v1/")):
        return error_response(404, "Not found.")
    return not_found_page()


@app.get("/classic")
def classic():
    """The earlier chat-ui (Vue) page, kept for reference."""
    return send_from_directory(app.static_folder, "classic.html")


MAX_EXTRACT_CHARS = 60_000


@app.post("/api/extract")
def extract_document():
    """Text of an attached PDF, Word, Markdown or text file, so any provider can read it."""
    file = request.files.get("file")
    if not file or not file.filename:
        return error_response(400, "Choose a file.")
    name, data = file.filename, file.read()
    try:
        if name.lower().endswith(".pdf"):
            from pypdf import PdfReader
            text = "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        elif name.lower().endswith((".docx", ".txt", ".md", ".csv", ".json")):
            text = extract_text(name, data)
        else:
            return error_response(400, f"{name}: attach a PDF, Word, text or image file.")
    except Exception as exc:
        return error_response(400, f"Couldn't read {name}: {exc}")
    text = text.strip()
    if not text:
        return error_response(400, f"{name} has no readable text (it may be a scanned PDF; attach a photo of it instead).")
    truncated = len(text) > MAX_EXTRACT_CHARS
    return jsonify({"name": name, "text": text[:MAX_EXTRACT_CHARS], "truncated": truncated})


@app.get("/api/providers")
def list_providers():
    reload_env()
    all_providers = providers.load()
    return jsonify({"providers": providers.public_list(all_providers), "default": providers.default_name(all_providers)})


@app.get("/api/datasets")
def list_datasets():
    return jsonify({"datasets": dataset.list_datasets()})


@app.post("/api/datasets")
def upload_dataset():
    file = request.files.get("file")
    if not file or not file.filename:
        return error_response(400, "Choose a file to upload.")
    try:
        name = dataset.save_dataset(file.filename, file.read())
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        return error_response(400, f"Couldn't read that file: {exc}")
    return jsonify({"name": name, "datasets": dataset.list_datasets()})


@app.delete("/api/datasets/<name>")
def delete_dataset(name: str):
    try:
        dataset.delete_dataset(name)
    except ValueError as exc:
        return error_response(400, str(exc))
    return jsonify({"datasets": dataset.list_datasets()})


@app.post("/v1/chat/completions")
def chat_completions():
    body = request.get_json(silent=True) or {}
    reload_env()
    all_providers = providers.load()
    provider = all_providers.get(body.get("provider") or providers.default_name(all_providers))
    if not provider:
        return error_response(400, f"Unknown provider: {body.get('provider')}")
    if not provider["api_key"] and provider["kind"] == "anthropic":
        return error_response(500, "No API key for Claude. Put ANTHROPIC_API_KEY in the .env file and restart.")

    instructions, messages = split_messages(body.get("messages") or [])
    if not messages:
        return error_response(400, "Type a question first.")

    passages = []
    if body.get("datasets"):
        try:
            top_k = max(1, min(int(body.get("top_k") or 5), 20))
        except (TypeError, ValueError):
            top_k = 5
        passages = dataset.search(retrieval_query(messages), list(body["datasets"]), top_k)

    system = build_system_prompt(
        body.get("jurisdiction") or "India",
        language=body.get("language") or None,
        custom_instructions=instructions,
        web_search=provider["kind"] == "anthropic" and bool(body.get("web_search")),
        passages=passages,
    )
    notes = passages_note(passages)
    if provider["kind"] == "anthropic":
        return call_claude(provider, body, system, messages, notes)
    return call_openai_compatible(provider, body, system, messages, notes)


def port_in_use(port: int) -> bool:
    """True if something already answers on the port.

    On Windows two servers can listen on the same port at once, and the old one
    keeps answering, so the browser shows stale pages. Check before starting.
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    import sys
    port = int(os.getenv("PORT", "8000"))
    if port_in_use(port):
        print(f"Port {port} is already in use: another copy of the server is probably still running.\n"
              f"Close its window or press Ctrl+C there, then start this again "
              f"(or set PORT=8001 in .env to use another port).")
        sys.exit(1)
    print(f"Constitution Ai running at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, threaded=True)
