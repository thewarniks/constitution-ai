"""Streaming calls to Claude.

stream_answer() yields (kind, value) events so the UI can update as text
arrives, like the old chat-ui's read()/parseChoice() loop that appended
content and reasoning_content to the last message chunk by chunk.
"""

import anthropic

# Models that support the server-side refusal fallback (fallbacks="default").
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
MAX_CONTINUATIONS = 3


def stream_answer(
    client: anthropic.Anthropic,
    messages: list[dict],
    system: str,
    *,
    model: str,
    effort: str,
    show_thinking: bool,
    web_search: bool,
):
    """Yield ("thinking" | "text" | "status", str) while streaming, then ("done", info)."""
    params = {
        "model": model,
        "max_tokens": 64000,
        "system": system,
        "thinking": {"type": "adaptive", "display": "summarized" if show_thinking else "omitted"},
        "output_config": {"effort": effort},
        # Caches the conversation prefix (including attached documents) between turns.
        "cache_control": {"type": "ephemeral"},
    }
    if model in FALLBACK_MODELS:
        # If a safety classifier declines, the API retries on a fallback model
        # in the same call instead of returning an empty refusal.
        params["betas"] = ["server-side-fallback-2026-07-01"]
        params["fallbacks"] = "default"
    if web_search:
        params["tools"] = [WEB_SEARCH_TOOL]

    convo = list(messages)
    sources: dict[str, str] = {}
    for _ in range(MAX_CONTINUATIONS + 1):
        with client.beta.messages.stream(messages=convo, **params) as stream:
            for event in stream:
                if event.type == "content_block_start" and event.content_block.type == "server_tool_use":
                    yield "status", "Searching the web…"
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        yield "thinking", event.delta.thinking
                    elif event.delta.type == "text_delta":
                        yield "text", event.delta.text
            final = stream.get_final_message()

        for block in final.content:
            for citation in getattr(block, "citations", None) or []:
                url = getattr(citation, "url", None)
                if url:
                    sources.setdefault(url, getattr(citation, "title", None) or url)

        # A server tool (web search) hit its iteration limit mid-turn: send the
        # partial turn back so Claude can carry on from where it stopped.
        if final.stop_reason != "pause_turn":
            break
        convo.append({"role": "assistant", "content": final.content})

    yield "done", {"stop_reason": final.stop_reason, "sources": sources}
