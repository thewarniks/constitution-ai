"""Saved conversations, one JSON file per chat in ./history.

The old chat-ui kept history in the browser's localStorage. Here it lives on
disk so it survives restarts and can be backed up.
"""

import json
from datetime import datetime
from pathlib import Path

HISTORY_DIR = Path(__file__).parent / "history"


def new_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def title_of(messages: list[dict]) -> str:
    first = next((m for m in messages if m["role"] == "user"), None)
    if not first:
        return "Empty chat"
    text = first["content"] if isinstance(first["content"], str) else next(
        (b["text"] for b in first["content"] if b.get("type") == "text"), "Attachment"
    )
    return text[:60] + ("…" if len(text) > 60 else "")


def save(chat_id: str, messages: list[dict], settings: dict) -> None:
    HISTORY_DIR.mkdir(exist_ok=True)
    record = {
        "id": chat_id,
        "title": title_of(messages),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "settings": settings,
        "messages": messages,
    }
    (HISTORY_DIR / f"{chat_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def load(chat_id: str) -> dict:
    return json.loads((HISTORY_DIR / f"{chat_id}.json").read_text(encoding="utf-8"))


def list_chats() -> list[dict]:
    """Newest first, without the messages."""
    chats = []
    for path in HISTORY_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        chats.append({k: record.get(k) for k in ("id", "title", "updated")})
    return sorted(chats, key=lambda c: c["updated"] or "", reverse=True)


def delete(chat_id: str) -> None:
    (HISTORY_DIR / f"{chat_id}.json").unlink(missing_ok=True)


def delete_all() -> None:
    for path in HISTORY_DIR.glob("*.json"):
        path.unlink(missing_ok=True)


def to_markdown(messages: list[dict]) -> str:
    """A readable transcript, e.g. to share with a lawyer."""
    lines = ["# Legal Help Assistant transcript", ""]
    for m in messages:
        who = "You" if m["role"] == "user" else "Assistant"
        if isinstance(m["content"], str):
            body = m["content"]
        else:
            parts = []
            for b in m["content"]:
                if b.get("type") == "text":
                    parts.append(b["text"])
                elif b.get("type") == "document":
                    parts.append(f"[Attached: {b.get('title', 'document')}]")
                elif b.get("type") == "image":
                    parts.append("[Attached image]")
            body = "\n\n".join(parts)
        lines += [f"## {who}", "", body, ""]
    return "\n".join(lines)
