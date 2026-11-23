"""Website pages for Constitution Ai (layouts adapted from the Aigocy template).

Registered on the Flask app in server.py. Page text lives in site_content.py;
the chat page talks to the same /v1/chat/completions backend as the dashboard.
"""

import json
import threading
import time
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, jsonify, render_template, request, send_from_directory

from . import site_content as content

HERE = Path(__file__).parent
ASSETS_DIR = HERE / "static" / "assets"
MESSAGES_FILE = HERE.parent / "contact_messages.jsonl"
REVIEWED = "November 2026"
ASSET_VERSION = str(int(time.time()))  # appended to our CSS/JS links so browsers pick up edits after a restart

bp = Blueprint("website", __name__, template_folder="templates")

_contact_lock = threading.Lock()
_recent_posts: dict[str, deque] = {}
CONTACT_LIMIT, CONTACT_WINDOW = 5, 600  # at most 5 messages per 10 minutes per visitor


@bp.app_context_processor
def common_context():
    return {
        "site": content.SITE,
        # "Constitution Ai" -> "Constitution" + "Ai" (accent colour in the logo)
        "brand_main": content.SITE["name"].rsplit(" ", 1)[0],
        "brand_accent": content.SITE["name"].rsplit(" ", 1)[-1] if " " in content.SITE["name"] else "",
        "disclaimer": content.DISCLAIMER,
        "areas": content.AREAS,
        "cases": content.CASES,
        "guides": content.GUIDES,
        "faqs": content.FAQS,
        "stats": content.STATS,
        "providers": content.PROVIDERS,
        "languages": content.LANGUAGES,
        "area_titles": {a["slug"]: a["title"] for a in content.AREAS},
        "reviewed": REVIEWED,
        "v": ASSET_VERSION,
        "year": date.today().year,
    }


@bp.get("/assets/<path:filename>")
def assets(filename):
    # max_age=0: browsers re-check (cheap 304s), so edited images and styles show up right away.
    return send_from_directory(ASSETS_DIR, filename, max_age=0)


@bp.get("/")
def home():
    return render_template("index.html", page="home")


@bp.get("/about")
def about():
    return render_template("about.html", page="about")


@bp.get("/practice-areas")
def areas():
    return render_template("areas.html", page="areas")


@bp.get("/practice-areas/<slug>")
def area(slug):
    item = content.area(slug) or abort(404)
    related = next((c for c in content.CASES if c["area"] == slug), None)
    return render_template("area.html", page="areas", area=item, related_case=related)


@bp.get("/use-cases")
def cases():
    return render_template("cases.html", page="cases")


@bp.get("/use-cases/<slug>")
def case(slug):
    item = content.case(slug) or abort(404)
    others = [c for c in content.CASES if c["slug"] != slug][:3]
    return render_template("case.html", page="cases", case=item, area=content.area(item["area"]), others=others)


@bp.get("/guides")
def guides():
    return render_template("guides.html", page="guides")


@bp.get("/guides/<slug>")
def guide(slug):
    item = content.guide(slug) or abort(404)
    others = [g for g in content.GUIDES if g["slug"] != slug][:4]
    return render_template("guide.html", page="guides", guide=item, others=others)


@bp.get("/contact")
def contact():
    return render_template("contact.html", page="contact")


@bp.get("/chat")
def chat():
    starters = [a["questions"][0] for a in content.AREAS]
    return render_template("chat.html", page="chat", starters=starters)


@bp.post("/api/contact")
def contact_submit():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:120]
    contact_info = str(data.get("contact", "")).strip()[:160]
    message = str(data.get("message", "")).strip()[:4000]
    if not (name and contact_info and message):
        return jsonify({"error": {"message": "Please fill in your name, contact details and message."}}), 400

    visitor = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    now = time.time()
    with _contact_lock:
        recent = _recent_posts.setdefault(visitor, deque())
        while recent and now - recent[0] > CONTACT_WINDOW:
            recent.popleft()
        if len(recent) >= CONTACT_LIMIT:
            return jsonify({"error": {"message": "Too many messages. Please try again in a few minutes."}}), 429
        recent.append(now)
        record = {
            "received": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "name": name,
            "contact": contact_info,
            "message": message,
        }
        with MESSAGES_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return jsonify({"ok": True})


def not_found_page():
    return render_template("404.html", page="404"), 404
