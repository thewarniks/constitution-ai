"""Export the website as plain HTML for GitHub Pages, into docs/.

GitHub Pages can't run Python, so this renders every page once with Flask's
test client and saves the result. Links are rewritten to relative paths so
the site works at https://<user>.github.io/<repo>/. The chat and contact form
need the Python server; on the static copy they show a short notice instead.

Usage:
    python export_static.py --base /<repo-name>/
    (use --base / for a <user>.github.io repository)
"""

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
ASSETS = ROOT / "website" / "static" / "assets"

ATTR = re.compile(r'(\b(?:href|src|action)=")(/(?!/)[^"]*)(")')
STATIC_FLAG = "<script>window.CA_STATIC = true;</script>\n</head>"


def page_routes():
    from website import site_content as c
    routes = ["/", "/about", "/practice-areas", "/use-cases", "/guides", "/contact", "/chat"]
    routes += [f"/practice-areas/{a['slug']}" for a in c.AREAS]
    routes += [f"/use-cases/{x['slug']}" for x in c.CASES]
    routes += [f"/guides/{g['slug']}" for g in c.GUIDES]
    return routes


def rewrite(html: str, prefix: str) -> str:
    """Turn root-relative links (/about, /assets/x.css) into links that work under any base path."""
    def fix(m):
        path, tail = re.match(r"([^?#]*)(.*)", m.group(2)).groups()  # tail keeps ?query and #fragment
        if path.startswith("/assets/"):
            new = prefix + path[1:]
        elif path in ("/app", "/classic") or path.startswith(("/api/", "/v1/")):
            new = prefix + "chat/"  # server-only features: point to the chat page, which explains
        else:
            p = path.strip("/")
            new = prefix + (p + "/" if p else "")
        return m.group(1) + (new or "./") + tail + m.group(3)
    return ATTR.sub(fix, html)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="/", help="URL path the site is served from, e.g. /constitution-ai/")
    args = parser.parse_args()
    base = "/" + args.base.strip("/") + "/" if args.base.strip("/") else "/"

    import server  # noqa: E402  (imports the Flask app with the website blueprint)
    client = server.app.test_client()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ASSETS, OUT / "assets")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    for route in page_routes():
        resp = client.get(route)
        if resp.status_code != 200:
            raise SystemExit(f"{route} returned {resp.status_code}")
        depth = len([p for p in route.strip("/").split("/") if p])
        html = resp.get_data(as_text=True).replace("</head>", STATIC_FLAG, 1)
        html = rewrite(html, "../" * depth)
        target = OUT / route.strip("/") / "index.html" if depth else OUT / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print("exported", route)

    # GitHub Pages shows 404.html for unknown URLs at any depth, so it needs absolute links.
    resp = client.get("/this-page-does-not-exist")
    html = resp.get_data(as_text=True).replace("</head>", STATIC_FLAG, 1)
    (OUT / "404.html").write_text(rewrite(html, base), encoding="utf-8")
    print(f"exported 404.html (base {base})")
    print(f"done: {OUT}")


if __name__ == "__main__":
    main()
