#!/usr/bin/env python3
"""
Share the newest blog post to the Adie's Electrical Facebook Page.

Runs in GitHub Actions right after the weekly blog post is published.
Needs two repository secrets:
  FB_PAGE_ID     - the numeric ID of the Facebook Page
  FB_PAGE_TOKEN  - a long-lived Page access token with pages_manage_posts

If either secret is missing the script prints a note and exits cleanly,
so the blog pipeline never fails because of Facebook.

Usage:
  python post_to_facebook.py                 # share the newest dated post
  python post_to_facebook.py blog/<file>.html  # share a specific post
"""

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://adieselectrical.co.za"
BLOG_DIR = "blog"
GRAPH_VERSION = os.environ.get("FB_GRAPH_VERSION", "v23.0")
WHATSAPP = "084 785 3823"
WHATSAPP_LINK = "https://wa.me/27847853823"


def newest_post() -> str:
    files = sorted(
        f for f in os.listdir(BLOG_DIR)
        if re.match(r"^\d{4}-\d{2}-\d{2}-.+\.html$", f)
    )
    if not files:
        sys.exit("No dated blog posts found.")
    return os.path.join(BLOG_DIR, files[-1])


def meta(page: str, prop: str) -> str:
    m = re.search(
        rf'<meta[^>]+(?:property|name)="{re.escape(prop)}"[^>]+content="([^"]*)"',
        page, re.IGNORECASE,
    )
    return html.unescape(m.group(1)).strip() if m else ""


def read_post(path: str):
    with open(path, encoding="utf-8") as f:
        page = f.read()
    title = meta(page, "og:title")
    if not title:
        m = re.search(r"<title>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
        title = html.unescape(m.group(1)).strip() if m else ""
    title = re.sub(r"\s*\|\s*Adie.*$", "", title)  # drop "| Adie's Electrical" suffix
    desc = meta(page, "og:description") or meta(page, "description")
    url = f"{SITE}/blog/{os.path.basename(path)}"
    return title, desc, url


def wait_until_live(url: str, timeout: int = 420) -> bool:
    """GitHub Pages takes a minute or two to publish after the push."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fb-share-check"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(20)
    return False


def build_message(title: str, desc: str) -> str:
    lines = [f"\U0001F4A1 New on the blog: {title}"]
    # Meta descriptions are cut at 160 chars; end on a whole word.
    if desc and len(desc) >= 150 and desc[-1] not in ".!?":
        desc = desc[: desc.rfind(" ")].rstrip(" ,;:-—") + "…"
    if desc:
        lines += ["", desc]
    lines += [
        "",
        f"Need an electrician in Cape Town? WhatsApp Adie on {WHATSAPP} \U0001F449 {WHATSAPP_LINK}",
        "",
        "#CapeTown #Electrician #AdiesElectrical",
    ]
    return "\n".join(lines)


def post(page_id: str, token: str, message: str, link: str) -> dict:
    data = urllib.parse.urlencode(
        {"message": message, "link": link, "access_token": token}
    ).encode()
    endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed"
    req = urllib.request.Request(endpoint, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"Facebook API error {e.code}: {body}")


def main():
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    if not page_id or not token:
        print("FB_PAGE_ID / FB_PAGE_TOKEN not set - skipping Facebook post.")
        return

    path = sys.argv[1] if len(sys.argv) > 1 else newest_post()
    title, desc, url = read_post(path)
    print(f"Sharing: {title}\n{url}")

    if not wait_until_live(url):
        print("Post isn't live yet; sharing anyway (Facebook will fetch the preview later).")

    result = post(page_id, token, build_message(title, desc), url)
    print(f"Posted to Facebook: {result.get('id')}")


if __name__ == "__main__":
    main()
