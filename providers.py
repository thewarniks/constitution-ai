"""Model providers, loaded from the old chat-ui config files in ./providers.

Each JSON file has the same shape the old page imported ("chatbotStore" with
url, path, model, apiKey, max_tokens_type/value, and "defaultChoiceStore"
with the model list), so you can drop in more of them. The request is sent
the same way the old page's createCompletion() did: POST url + path with an
"Authorization: Bearer <key>" header and an OpenAI-style body.

Optional extra fields in a provider file:
  "title":          name shown in the provider list
  "modelsUrl":      OpenAI-style GET /models endpoint; the live list replaces
                    the static one (free model line-ups change often)
  "modelsExclude":  skip live models whose id contains any of these words
  "modelsFreeOnly": keep only free models (OpenRouter: ":free" ids or $0 pricing)
  "keyRequired":    false for local servers such as Ollama
  "headers":        extra HTTP headers to send (e.g. Hive needs "Accept: text/event-stream")
  "body":           extra fields to add to every request body (e.g. "reasoning_effort")

API keys: an environment variable <NAME>_API_KEY (from .env) wins, e.g.
DEEPSEEK_API_KEY for deepseek.json or GROQ_API_KEY for groq.json.
Otherwise the apiKey inside the JSON file is used. Keys never go to the browser.
"""

import json
import os
import re
import time
from pathlib import Path

import requests

PROVIDERS_DIR = Path(__file__).parent / "providers"
CLAUDE_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
TITLES = {
    "deepseek": "DeepSeek",
    "chatgpt": "OpenAI ChatGPT",
    "chatgptproxy": "ChatGPT (AIQL proxy)",
    "deepinfra": "DeepInfra",
    "ali-qwen": "Alibaba Qwen",
    "nvidiaNIM": "NVIDIA NIM",
}
# Without DEFAULT_PROVIDER, the first of these that has a key is selected.
PREFERRED_DEFAULTS = ["claude", "hive", "groq", "gemini", "openrouter", "deepseek"]
MODEL_LIST_TTL = 600  # seconds to cache a live model list
MODEL_LIST_RETRY = 60  # seconds before retrying after a failed fetch

_model_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}


def env_key_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", name.upper()) + "_API_KEY"


def _key(value: str | None) -> str:
    """Treat empty values and template placeholders like "your-...-here" as no key."""
    value = (value or "").strip()
    return "" if not value or value.lower().startswith("your-") else value


def _is_free(model: dict) -> bool:
    pricing = model.get("pricing") or {}
    return model.get("id", "").endswith(":free") or (
        str(pricing.get("prompt")) in ("0", "0.0") and str(pricing.get("completion")) in ("0", "0.0")
    )


def _live_models(name: str, cfg: dict, api_key: str) -> list[str]:
    """Fetch the provider's current model ids, cached. Empty list if unavailable."""
    url = cfg.get("modelsUrl")
    needs_key = cfg.get("keyRequired", True)
    if not url or (needs_key and not api_key and not cfg.get("modelsFreeOnly")):
        return []
    cache_key = (name, api_key)
    cached = _model_cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]

    models: list[str] = []
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        local = url.startswith("http://localhost") or url.startswith("http://127.0.0.1")
        resp = requests.get(url, headers=headers, timeout=0.8 if local else 6)
        resp.raise_for_status()
        data = resp.json().get("data") or []
        exclude = [w.lower() for w in cfg.get("modelsExclude") or []]
        for m in data:
            model_id = str(m.get("id", "")).removeprefix("models/")
            if not model_id or any(w in model_id.lower() for w in exclude):
                continue
            if cfg.get("modelsFreeOnly") and not _is_free(m):
                continue
            outputs = (m.get("architecture") or {}).get("output_modalities")
            if outputs and "text" not in outputs:  # e.g. music or image generators
                continue
            models.append(model_id)
        models.sort()
        ttl = MODEL_LIST_TTL
    except (requests.RequestException, ValueError, AttributeError):
        ttl = MODEL_LIST_RETRY
    _model_cache[cache_key] = (time.time() + ttl, models)
    return models


def load() -> dict[str, dict]:
    providers = {}
    for path in sorted(PROVIDERS_DIR.glob("*.json")):
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        store = cfg.get("chatbotStore") or {}
        if not store.get("url"):
            continue
        name = path.stem
        api_key = _key(os.getenv(env_key_name(name))) or _key(store.get("apiKey"))
        default_model = store.get("model") or ""
        models = (cfg.get("defaultChoiceStore") or {}).get("model") or [default_model]

        live = _live_models(name, cfg, api_key)
        if live:
            # Keep the configured picks (e.g. the "openrouter/free" router) at the top if still offered.
            pinned = [m for m in models if m in live or m == "openrouter/free"]
            models = pinned + [m for m in live if m not in pinned]
            if default_model not in models:
                default_model = models[0]

        providers[name] = {
            "name": name,
            "title": cfg.get("title") or TITLES.get(name, name),
            "kind": "openai",
            "url": store["url"].rstrip("/") + (store.get("path") or "/v1/chat/completions"),
            "auth_prefix": store.get("authPrefix") or "Bearer",
            "default_model": default_model,
            "models": models,
            "max_tokens_type": store.get("max_tokens_type") or "max_tokens",
            "max_tokens_value": str(store.get("max_tokens_value") or ""),
            "api_key": api_key,
            "needs_key": cfg.get("keyRequired", True),
            "reachable": bool(live) if cfg.get("modelsUrl") else None,  # None = not checked
            "extra_headers": cfg.get("headers") or {},
            "extra_body": cfg.get("body") or {},
        }
    providers["claude"] = {
        "name": "claude",
        "title": "Anthropic Claude",
        "kind": "anthropic",
        "default_model": os.getenv("CLAUDE_MODEL", CLAUDE_MODELS[0]),
        "models": CLAUDE_MODELS,
        "api_key": _key(os.getenv("ANTHROPIC_API_KEY")),
        "needs_key": True,
    }
    return providers


def is_ready(provider: dict) -> bool:
    return bool(provider["api_key"]) or not provider.get("needs_key", True)


def public_list(providers: dict[str, dict]) -> list[dict]:
    """What the browser may see: no keys, no upstream URLs."""
    return [
        {
            "name": p["name"],
            "title": p["title"],
            "models": p["models"],
            "default_model": p["default_model"],
            "has_key": is_ready(p),
            "env_key": "ANTHROPIC_API_KEY" if p["kind"] == "anthropic" else env_key_name(p["name"]),
        }
        for p in providers.values()
    ]


def default_name(providers: dict[str, dict]) -> str:
    """DEFAULT_PROVIDER from .env, else the first preferred provider with a key, else any with a key."""
    wanted = os.getenv("DEFAULT_PROVIDER", "").strip()
    if wanted in providers:
        return wanted
    for name in PREFERRED_DEFAULTS:
        if name in providers and providers[name]["api_key"]:
            return name
    with_key = [n for n, p in providers.items() if p["api_key"]]
    return with_key[0] if with_key else next(iter(providers))
