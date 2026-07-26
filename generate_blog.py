#!/usr/bin/env python3
"""
generate_blog.py

Automated weekly SEO blog post generator for Adie's Electrical Solutions
(Cape Town electrician business). Uses the Google Gemini API to write a
localized, SEO-friendly blog post as a standalone HTML file and saves it
into the blog/ folder.

Environment variables required:
    GEMINI_API_KEY - API key for Google Gemini (https://ai.google.dev/)

Usage:
    python generate_blog.py
"""

import os
import re
import sys
import random
import unicodedata
from datetime import date, datetime

try:
    from google import genai
except ImportError:
    print(
        "ERROR: 'google-genai' package is not installed.\n"
        "Install it with: pip install google-genai",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BLOG_DIR = "blog"
MODEL_NAME = "gemini-2.0-flash"  # fast + cheap, good enough for blog copy

BUSINESS_NAME = "Adie's Electrical Solutions"
BUSINESS_LOCATION = "Cape Town Metro (Retreat)"
BUSINESS_PHONE_WHATSAPP = "+27 84 729 9088"
BUSINESS_EMAIL = "info@adieselectrical.co.za"
BUSINESS_WEBSITE = "https://adieselectrical.co.za"

# Rotating pool of local, SEO-relevant topics. The script picks one at
# random each run and asks Gemini to avoid duplicating a topic already
# used (see `get_existing_slugs`).
TOPIC_POOL = [
    "How much does a DB board upgrade cost in Cape Town",
    "Do I need a COC to sell my house in Cape Town",
    "Signs your home needs an electrical fault finding inspection",
    "Load shedding: how to protect your home's electrical system",
    "Solar installation costs and benefits for Cape Town homeowners",
    "What is a COC and why every property sale in South Africa needs one",
    "Common electrical faults found in older Cape Town homes",
    "How to choose a qualified and licensed electrician in Cape Town",
    "DB board safety: why outdated boards are a fire risk",
    "Electrical maintenance checklist for landlords and body corporates",
    "Understanding your home's earth leakage and circuit breakers",
    "Preparing your home's electrics for solar and battery backup",
    "What to expect during a residential electrical compliance inspection",
    "How load shedding stages affect inverter and solar system sizing",
    "Why DIY electrical work is illegal and dangerous in South Africa",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def check_environment() -> str:
    """Verify required environment variables and return the API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY environment variable is not set.\n"
            "Set it locally with:\n"
            "  export GEMINI_API_KEY='your-key-here'\n"
            "Or add it as a GitHub Actions secret named GEMINI_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key


def slugify(text: str) -> str:
    """Convert a string into a safe, URL/filename-friendly slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    text = re.sub(r"-+", "-", text)
    return text[:80] or "blog-post"


def get_existing_slugs() -> set:
    """Return the set of slugs already used in the blog/ folder, so we can
    nudge Gemini away from repeating a topic it already covered."""
    if not os.path.isdir(BLOG_DIR):
        return set()
    slugs = set()
    for fname in os.listdir(BLOG_DIR):
        if fname.endswith(".html"):
            # filenames are like: 2026-07-26-db-board-upgrade-cost.html
            base = fname[:-5]
            parts = base.split("-", 3)
            if len(parts) == 4:
                slugs.add(parts[3])
    return slugs


def choose_topic() -> str:
    """Pick a topic from the pool, preferring ones not already used."""
    existing = get_existing_slugs()
    unused = [t for t in TOPIC_POOL if slugify(t) not in existing]
    pool = unused if unused else TOPIC_POOL
    return random.choice(pool)


def build_prompt(topic: str) -> str:
    return f"""You are an SEO copywriter for a local electrician business.

Business details:
- Name: {BUSINESS_NAME}
- Service area: {BUSINESS_LOCATION}, South Africa
- Contact: WhatsApp {BUSINESS_PHONE_WHATSAPP}, email {BUSINESS_EMAIL}
- Website: {BUSINESS_WEBSITE}

Write a complete, publish-ready SEO blog post on this topic:
"{topic}"

Requirements:
- Target local Cape Town homeowners and landlords searching for electrical services.
- Include a clear, keyword-rich H1 title (different from a generic restatement -
  make it specific and searchable).
- Structure with H2/H3 subheadings, short paragraphs, and at least one bullet list.
- Naturally mention {BUSINESS_NAME} once or twice as the trusted local expert,
  and include a call-to-action near the end encouraging the reader to contact
  via WhatsApp ({BUSINESS_PHONE_WHATSAPP}) or email ({BUSINESS_EMAIL}) for a quote
  or inspection.
- Word count: roughly 600-900 words.
- Tone: practical, trustworthy, plain-English — avoid technical jargon without
  explaining it simply.
- Do NOT include any pricing that could be inaccurate or misleading; use ranges
  and note that final pricing depends on an on-site assessment.
- Output ONLY the raw inner body HTML for the article (use tags like <h1>, <h2>,
  <h3>, <p>, <ul>, <li>, <strong>, <a>). Do NOT include <html>, <head>, <body>,
  markdown code fences, or any commentary outside the HTML.
"""


def generate_article_html(api_key: str, topic: str) -> str:
    client = genai.Client(api_key=api_key)

    prompt = build_prompt(topic)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    text = (response.text or "").strip()

    # Defensive cleanup in case the model wraps output in code fences anyway.
    text = re.sub(r"^```(?:html)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    if not text:
        print("ERROR: Gemini returned an empty response.", file=sys.stderr)
        sys.exit(1)

    return text


def extract_title(article_html: str, fallback: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", article_html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if title:
            return title
    return fallback


def wrap_full_page(article_html: str, title: str, meta_description: str) -> str:
    """Wrap the generated article body in a full, standalone HTML page."""
    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="en-za">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {BUSINESS_NAME}</title>
<meta name="description" content="{meta_description}">
<meta name="author" content="{BUSINESS_NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_description}">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{today}">
<link rel="stylesheet" href="../styles.css">
</head>
<body>
<main class="blog-post">
<article>
{article_html}
</article>
<hr>
<p><a href="../index.html">&larr; Back to {BUSINESS_NAME} home</a></p>
</main>
</body>
</html>
"""


def main():
    api_key = check_environment()

    os.makedirs(BLOG_DIR, exist_ok=True)

    topic = choose_topic()
    print(f"Selected topic: {topic}")

    article_html = generate_article_html(api_key, topic)
    title = extract_title(article_html, fallback=topic)

    # Simple meta description: strip tags from the first <p> paragraph.
    p_match = re.search(r"<p[^>]*>(.*?)</p>", article_html, re.IGNORECASE | re.DOTALL)
    if p_match:
        meta_description = re.sub(r"<[^>]+>", "", p_match.group(1)).strip()[:160]
    else:
        meta_description = title

    full_page = wrap_full_page(article_html, title, meta_description)

    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title if title else topic)
    filename = f"{today_str}-{slug}.html"
    filepath = os.path.join(BLOG_DIR, filename)

    # Guard against accidental overwrite / path traversal.
    safe_path = os.path.normpath(filepath)
    if not safe_path.startswith(BLOG_DIR + os.sep) and safe_path != BLOG_DIR:
        print("ERROR: unsafe file path generated, aborting.", file=sys.stderr)
        sys.exit(1)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(full_page)

    print(f"Blog post written to: {safe_path}")


if __name__ == "__main__":
    main()
