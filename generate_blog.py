#!/usr/bin/env python3
"""
generate_blog.py

Automated weekly SEO blog post generator for Adie's Electrical Solutions
(Cape Town electrician business). Uses OpenRouter (free tier, OpenAI-compatible
API) to write a localized, SEO-friendly blog post as a standalone HTML file
and saves it into the blog/ folder.

NOTE: This previously ran on GitHub Models, which was permanently retired
by GitHub on July 30, 2026. It now points at OpenRouter instead - same
OpenAI SDK, just a different base_url, api key, and model name.

Environment variables required:
    OPENROUTER_API_KEY - Your OpenRouter API key (free, no card required).
                          Sign up at https://openrouter.ai/keys, generate a
                          key, then add it as a GitHub Actions repo secret
                          named OPENROUTER_API_KEY (Settings -> Secrets and
                          variables -> Actions -> New repository secret).

Usage:
    python generate_blog.py
"""

import os
import re
import sys
import json
import random
import unicodedata
from datetime import date, datetime

try:
    from openai import OpenAI
except ImportError:
    print(
        "ERROR: 'openai' package is not installed.\n"
        "Install it with: pip install openai",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BLOG_DIR = "blog"

# OpenRouter exposes an OpenAI-compatible endpoint. Auth uses an OpenRouter
# API key (free, no card required - see https://openrouter.ai/keys), stored
# as the OPENROUTER_API_KEY repo secret in GitHub Actions.
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
MODEL_NAME = "openrouter/free"

BUSINESS_NAME = "Adie's Electrical Solutions"
BUSINESS_LOCATION = "Cape Town Metro (Retreat)"
BUSINESS_PHONE_WHATSAPP = "+27 84 729 9088"
BUSINESS_EMAIL = "info@adieselectrical.co.za"
BUSINESS_WEBSITE = "https://adieselectrical.co.za"

TOPICS_FILE = "topics.json"

# Fallback pool, used only if topics.json is missing or unreadable, so the
# script never hard-fails just because that file didn't make it into the
# repo for some reason.
FALLBACK_TOPIC_POOL = [
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


def load_topic_pool() -> list:
    """Load the topic pool from topics.json (real customer questions,
    e.g. sourced from Reddit/AnswerThePublic research), falling back to a
    small built-in list if the file is missing, empty, or invalid."""
    if os.path.exists(TOPICS_FILE):
        try:
            with open(TOPICS_FILE, "r", encoding="utf-8") as f:
                topics = json.load(f)
            if isinstance(topics, list) and topics:
                return topics
            print(f"WARNING: {TOPICS_FILE} was empty or not a list - using fallback topics.")
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: could not read {TOPICS_FILE} ({e}) - using fallback topics.")
    else:
        print(f"WARNING: {TOPICS_FILE} not found - using fallback topics.")
    return FALLBACK_TOPIC_POOL


TOPIC_POOL = load_topic_pool()


WHATSAPP_LINK = "https://wa.me/27847299088?text=Hi%20Adie%2C%20I%27d%20like%20a%20quote%20for%20electrical%20work"

# Shared CSS variables + base rules, lifted from the main site so blog
# pages feel like part of the same site rather than a generic template.
SHARED_STYLE = """
  :root{
    --charcoal-black:#14120F;
    --charcoal:#201D1A;
    --charcoal-soft:#2B2723;
    --copper:#B87333;
    --copper-light:#D98B4A;
    --amber:#F2A93B;
    --cream:#F6F0E4;
    --cream-dim:#DCD3C0;
    --line:rgba(246,240,228,0.12);
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  html{scroll-behavior:smooth;}
  body{
    background:var(--charcoal-black);
    color:var(--cream);
    font-family:'Karla',sans-serif;
    line-height:1.6;
    overflow-x:hidden;
  }
  h1,h2,h3,.eyebrow,.logo-word,.nav-link,.btn{
    font-family:'Oswald',sans-serif;
    text-transform:uppercase;
    letter-spacing:0.03em;
  }
  a{color:inherit;text-decoration:none;}
  ul{list-style:none;}
  img,svg{display:block;max-width:100%;}
  .wrap{max-width:1120px;margin:0 auto;}

  /* ---------- Nav ---------- */
  header{
    position:sticky;top:0;z-index:50;
    background:rgba(20,18,15,0.9);
    backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line);
  }
  .nav{
    max-width:1120px;margin:0 auto;
    display:flex;align-items:center;justify-content:space-between;
    padding:14px 24px;
  }
  .brand{display:flex;align-items:center;gap:12px;}
  .brand svg{width:40px;height:40px;}
  .logo-word{font-size:1.05rem;font-weight:600;color:var(--cream);}
  .logo-word span{color:var(--copper-light);}
  .nav-links{display:flex;gap:28px;}
  .nav-link{font-size:0.8rem;font-weight:500;color:var(--cream-dim);transition:color .2s;}
  .nav-link:hover{color:var(--amber);}
  .nav-cta{
    background:var(--copper);
    color:var(--charcoal-black);
    padding:10px 18px;
    font-size:0.78rem;
    font-weight:600;
    border-radius:2px;
    transition:background .2s;
  }
  .nav-cta:hover{background:var(--amber);}
  .nav-toggle{display:none;background:none;border:none;color:var(--cream);font-size:1.5rem;cursor:pointer;}
  .eyebrow{
    font-size:0.78rem;color:var(--amber);font-weight:600;
    letter-spacing:0.12em;margin-bottom:18px;
    display:flex;align-items:center;gap:10px;
  }
  .eyebrow::before{content:"";width:26px;height:2px;background:var(--amber);}

  @media (max-width:760px){
    .nav-links{
      position:fixed;top:69px;left:0;right:0;
      background:var(--charcoal);
      flex-direction:column;
      padding:20px 24px;
      gap:18px;
      border-bottom:1px solid var(--line);
      transform:translateY(-140%);
      transition:transform .3s ease;
    }
    .nav-links.open{transform:translateY(0);}
    .nav-cta{display:none;}
    .nav-links .nav-cta{display:inline-block;width:fit-content;}
    .nav-toggle{display:block;}
  }

  /* ---------- Footer ---------- */
  footer{
    background:var(--charcoal);
    border-top:1px solid var(--line);
    padding:40px 24px;
  }
  .footer-wrap{
    max-width:1120px;margin:0 auto;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;
  }
  .footer-wrap p{color:var(--cream-dim);font-size:0.85rem;}

  /* ---------- WhatsApp float ---------- */
  .wa-float{
    position:fixed;bottom:24px;right:24px;z-index:60;
    background:#25D366;
    width:58px;height:58px;
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    box-shadow:0 6px 20px rgba(0,0,0,0.4);
    transition:transform .2s;
  }
  .wa-float:hover{transform:scale(1.08);}
  .wa-float svg{width:30px;height:30px;}
"""

# Header/nav markup, with links adjusted to work from inside the blog/
# subfolder (site sections use "../index.html#..", the Blog link points
# to the local index.html since we're already inside blog/).
SITE_HEADER = f"""<header>
  <nav class="nav">
    <div class="brand">
      <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#F2A93B"/>
            <stop offset="100%" stop-color="#B87333"/>
          </linearGradient>
        </defs>
        <circle cx="32" cy="32" r="31" fill="#201D1A" stroke="url(#logoGrad)" stroke-width="2"/>
        <path d="M35 12 L20 34 H29 L26 52 L45 26 H35 Z" fill="url(#logoGrad)"/>
      </svg>
      <a href="../index.html"><span class="logo-word">ADIE'S <span>ELECTRICAL</span></span></a>
    </div>
    <button class="nav-toggle" id="navToggle" aria-label="Toggle menu">&#9776;</button>
    <ul class="nav-links" id="navLinks">
      <li><a class="nav-link" href="../index.html#services">Services</a></li>
      <li><a class="nav-link" href="../index.html#work">Our Work</a></li>
      <li><a class="nav-link" href="../index.html#coc">COC</a></li>
      <li><a class="nav-link" href="index.html">Blog</a></li>
      <li><a class="nav-cta" href="../index.html#booking">Book a Job</a></li>
    </ul>
  </nav>
</header>"""

SITE_FOOTER = f"""<footer>
  <div class="footer-wrap">
    <p>&copy; {date.today().year} {BUSINESS_NAME}, Cape Town.</p>
    <p>{BUSINESS_PHONE_WHATSAPP.replace('+27 ', '0')} &middot; {BUSINESS_EMAIL}</p>
  </div>
</footer>

<a class="wa-float" href="{WHATSAPP_LINK}" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">
  <svg viewBox="0 0 32 32" fill="#fff"><path d="M16.001 2.667c-7.364 0-13.334 5.97-13.334 13.334 0 2.353.62 4.66 1.797 6.686L2.667 29.333l6.823-1.789a13.28 13.28 0 0 0 6.51 1.658h.001c7.364 0 13.334-5.97 13.334-13.334S23.365 2.667 16.001 2.667zm0 24.395a11.03 11.03 0 0 1-5.62-1.539l-.403-.24-4.05 1.062 1.081-3.947-.263-.405a11.01 11.01 0 0 1-1.686-5.86c0-6.09 4.955-11.045 11.046-11.045 6.09 0 11.045 4.955 11.045 11.045 0 6.09-4.955 11.045-11.05 11.045l-.1-.001zm6.06-8.272c-.332-.166-1.963-.968-2.268-1.078-.305-.11-.526-.166-.747.166-.222.332-.858 1.078-1.052 1.3-.194.222-.388.25-.72.083-.332-.166-1.401-.516-2.669-1.646-.987-.88-1.654-1.966-1.848-2.298-.194-.332-.021-.512.146-.677.15-.149.332-.388.499-.582.166-.194.222-.332.332-.554.11-.222.055-.416-.028-.582-.083-.166-.747-1.798-1.023-2.462-.27-.648-.544-.56-.747-.57-.194-.01-.416-.012-.638-.012-.222 0-.582.083-.887.416-.305.332-1.163 1.136-1.163 2.77 0 1.633 1.19 3.212 1.356 3.434.166.222 2.343 3.577 5.675 5.017.793.343 1.412.548 1.895.7.796.253 1.52.217 2.093.132.639-.095 1.963-.803 2.24-1.578.277-.775.277-1.44.194-1.578-.083-.138-.305-.222-.638-.388z"/></svg>
</a>

<script>
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  navToggle.addEventListener('click', () => navLinks.classList.toggle('open'));
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => navLinks.classList.remove('open')));
</script>"""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def check_environment() -> str:
    """Verify required environment variables and return the OpenRouter API key."""
    token = os.environ.get("OPENROUTER_API_KEY")
    if not token:
        print(
            "ERROR: OPENROUTER_API_KEY environment variable is not set.\n"
            "Inside GitHub Actions this must be added as a repo secret -\n"
            "Settings -> Secrets and variables -> Actions -> New repository\n"
            "secret, named OPENROUTER_API_KEY (see auto_blog.yml).\n"
            "For local runs, sign up for a free key at\n"
            "  https://openrouter.ai/keys\n"
            "and export it as OPENROUTER_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


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


def generate_article_html(token: str, topic: str) -> str:
    client = OpenAI(
        base_url=OPENROUTER_ENDPOINT,
        api_key=token,
    )

    prompt = build_prompt(topic)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )

    text = (response.choices[0].message.content or "").strip()

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


def generate_related_articles_html(current_filename: str = None, limit: int = 3) -> str:
    """Scan the blog/ folder for other posts and build a "Related Articles"
    section linking to up to `limit` of them, chosen at random for variety.
    Returns an empty string if there are no other posts yet (e.g. the very
    first post ever published)."""
    posts = []
    if os.path.isdir(BLOG_DIR):
        for fname in os.listdir(BLOG_DIR):
            if not fname.endswith(".html") or fname == "index.html":
                continue
            if current_filename and fname == current_filename:
                continue
            fpath = os.path.join(BLOG_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            # Skip consolidated/redirected pages (noindex stubs) so they never
            # get suggested as a "related" read - they just bounce the visitor
            # straight through to the canonical page anyway.
            if re.search(r'name="robots"\s+content="[^"]*noindex', content, re.IGNORECASE):
                continue

            title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            if not title_match:
                continue
            post_title = title_match.group(1).strip()
            post_title = re.sub(
                r"\s*\|\s*" + re.escape(BUSINESS_NAME) + r"\s*$",
                "", post_title, flags=re.IGNORECASE,
            )

            desc_match = re.search(r'<meta name="description" content="(.*?)">', content)
            description = desc_match.group(1).strip() if desc_match else ""
            if len(description) > 100:
                description = description[:97].rsplit(" ", 1)[0] + "..."

            posts.append({"filename": fname, "title": post_title, "description": description})

    if not posts:
        return ""

    random.shuffle(posts)
    chosen = posts[:limit]

    cards = ""
    for post in chosen:
        cards += f"""      <a class="related-card" href="{post['filename']}">
        <span class="related-label">Read Next</span>
        <h3>{post['title']}</h3>
        <p>{post['description']}</p>
      </a>
"""

    return f"""    <div class="related-articles">
      <h2>Related Articles</h2>
      <div class="related-grid">
{cards}      </div>
    </div>"""


def wrap_full_page(article_html: str, title: str, meta_description: str, related_html: str = "") -> str:
    """Wrap the generated article body in a full HTML page matching the
    main site's dark copper/amber theme (header, nav, footer, WhatsApp
    float button)."""
    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="en-za">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-Z69GM551P2"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-Z69GM551P2');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {BUSINESS_NAME}</title>
<meta name="description" content="{meta_description}">
<meta name="author" content="{BUSINESS_NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_description}">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{today}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{SHARED_STYLE}

  /* ---------- Blog post article ---------- */
  .blog-post{{padding:140px 24px 100px;background:var(--charcoal-black);}}
  .blog-post .wrap{{max-width:760px;}}
  .blog-post article h1{{
    font-size:clamp(2rem,4vw,2.8rem);
    color:var(--cream);
    font-weight:700;
    line-height:1.15;
    margin-bottom:28px;
  }}
  .blog-post article h2{{
    font-size:1.5rem;
    color:var(--cream);
    font-weight:600;
    margin:40px 0 16px;
  }}
  .blog-post article h3{{
    font-size:1.15rem;
    color:var(--copper-light);
    font-weight:600;
    margin:28px 0 12px;
  }}
  .blog-post article p{{color:var(--cream-dim);margin-bottom:18px;font-size:1.02rem;}}
  .blog-post article ul{{margin:0 0 20px 4px;}}
  .blog-post article li{{
    color:var(--cream-dim);
    padding:8px 0 8px 22px;
    position:relative;
    font-size:1rem;
  }}
  .blog-post article li::before{{
    content:"";
    position:absolute;left:0;top:17px;
    width:8px;height:8px;
    background:var(--copper);
    border-radius:1px;
  }}
  .blog-post article strong{{color:var(--cream);}}
  .blog-post article a{{color:var(--copper-light);border-bottom:1px solid var(--copper-light);}}
  .blog-post article a:hover{{color:var(--amber);border-bottom-color:var(--amber);}}
  .blog-post .back-link{{
    display:inline-block;margin-top:44px;
    color:var(--cream-dim);font-size:0.9rem;
    border-bottom:1px solid var(--line);
  }}
  .blog-post .back-link:hover{{color:var(--amber);}}

  /* ---------- Related articles ---------- */
  .related-articles{{margin-top:56px;padding-top:40px;border-top:1px solid var(--line);}}
  .related-articles h2{{
    font-size:1.3rem;color:var(--cream);font-weight:600;
    margin-bottom:20px;text-transform:none;letter-spacing:normal;
  }}
  .related-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}}
  .related-card{{
    display:block;background:var(--charcoal);
    border:1px solid var(--line);border-radius:4px;padding:20px;
    transition:border-color .2s, background .2s;
  }}
  .related-card:hover{{background:var(--charcoal-soft);border-color:var(--copper-light);}}
  .related-label{{
    font-family:'Oswald',sans-serif;font-size:0.68rem;letter-spacing:0.1em;
    color:var(--copper-light);text-transform:uppercase;
  }}
  .related-card h3{{
    font-size:0.98rem;color:var(--cream);font-weight:600;
    margin:8px 0 8px;text-transform:none;letter-spacing:normal;
  }}
  .related-card p{{color:var(--cream-dim);font-size:0.85rem;margin-bottom:0;}}
  @media (max-width:760px){{.related-grid{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>

{SITE_HEADER}

<section class="blog-post">
  <div class="wrap">
    <article>
{article_html}
    </article>
{related_html}
    <a class="back-link" href="index.html">&larr; Back to all articles</a>
  </div>
</section>

{SITE_FOOTER}

</body>
</html>
"""


def generate_index_html() -> str:
    """Scan the blog/ folder for existing posts and build an index page
    listing them as cards, newest first, matching the site's theme."""
    posts = []
    if os.path.isdir(BLOG_DIR):
        for fname in sorted(os.listdir(BLOG_DIR), reverse=True):
            if not fname.endswith(".html") or fname == "index.html":
                continue
            fpath = os.path.join(BLOG_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                # Strip a trailing " | Business Name" suffix if present,
                # but don't require it - some posts were added without it.
                title = re.sub(
                    r"\s*\|\s*" + re.escape(BUSINESS_NAME) + r"\s*$",
                    "", title, flags=re.IGNORECASE,
                )
            else:
                title = fname

            desc_match = re.search(r'<meta name="description" content="(.*?)">', content)
            description = desc_match.group(1).strip() if desc_match else ""

            date_match = re.match(r"(\d{4}-\d{2}-\d{2})-", fname)
            post_date = date_match.group(1) if date_match else ""

            posts.append({
                "filename": fname,
                "title": title,
                "description": description,
                "date": post_date,
            })

    cards_html = ""
    if not posts:
        cards_html = '<p class="no-posts">New articles are on the way - check back soon.</p>'
    else:
        for post in posts:
            cards_html += f"""      <a class="blog-card" href="{post['filename']}">
        <span class="blog-card-date">{post['date']}</span>
        <h3>{post['title']}</h3>
        <p>{post['description']}</p>
        <span class="blog-card-link">Read article &rarr;</span>
      </a>
"""

    return f"""<!DOCTYPE html>
<html lang="en-za">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-Z69GM551P2"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-Z69GM551P2');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog | {BUSINESS_NAME}</title>
<meta name="description" content="Electrical tips, guides, and local Cape Town advice from {BUSINESS_NAME} - COC inspections, DB board upgrades, solar, and more.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{SHARED_STYLE}

  /* ---------- Blog index ---------- */
  .blog-index{{padding:140px 24px 100px;background:var(--charcoal-black);}}
  .blog-index .section-head h1{{
    font-size:clamp(2rem,4vw,2.8rem);
    color:var(--cream);
    font-weight:700;
    margin-bottom:14px;
  }}
  .blog-index .section-head p{{color:var(--cream-dim);max-width:56ch;}}
  .blog-grid{{
    margin-top:48px;
    display:grid;grid-template-columns:repeat(2,1fr);gap:20px;
  }}
  .blog-card{{
    display:block;
    background:var(--charcoal);
    border:1px solid var(--line);
    border-radius:4px;
    padding:28px;
    transition:border-color .2s, background .2s;
  }}
  .blog-card:hover{{background:var(--charcoal-soft);border-color:var(--copper-light);}}
  .blog-card-date{{
    font-family:'Oswald',sans-serif;
    font-size:0.72rem;
    letter-spacing:0.08em;
    color:var(--copper-light);
    text-transform:uppercase;
  }}
  .blog-card h3{{
    font-size:1.15rem;color:var(--cream);font-weight:600;
    margin:10px 0 10px;text-transform:none;letter-spacing:normal;
  }}
  .blog-card p{{color:var(--cream-dim);font-size:0.92rem;margin-bottom:16px;}}
  .blog-card-link{{color:var(--amber);font-size:0.85rem;font-weight:600;}}
  .no-posts{{color:var(--cream-dim);}}

  @media (max-width:760px){{
    .blog-grid{{grid-template-columns:1fr;}}
  }}
</style>
</head>
<body>

{SITE_HEADER}

<section class="blog-index">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">Adie's Electrical Blog</div>
      <h1>Electrical Tips &amp; Local Cape Town Advice</h1>
      <p>Practical guides on DB boards, COC certificates, solar, and keeping your home's electrics safe - written for Cape Town homeowners and landlords.</p>
    </div>
    <div class="blog-grid">
{cards_html}    </div>
  </div>
</section>

{SITE_FOOTER}

</body>
</html>
"""


def main():
    token = check_environment()

    os.makedirs(BLOG_DIR, exist_ok=True)

    topic = choose_topic()
    print(f"Selected topic: {topic}")

    article_html = generate_article_html(token, topic)
    title = extract_title(article_html, fallback=topic)

    # Simple meta description: strip tags from the first <p> paragraph.
    p_match = re.search(r"<p[^>]*>(.*?)</p>", article_html, re.IGNORECASE | re.DOTALL)
    if p_match:
        meta_description = re.sub(r"<[^>]+>", "", p_match.group(1)).strip()[:160]
    else:
        meta_description = title

    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title if title else topic)
    filename = f"{today_str}-{slug}.html"
    filepath = os.path.join(BLOG_DIR, filename)

    # Guard against accidental overwrite / path traversal.
    safe_path = os.path.normpath(filepath)
    if not safe_path.startswith(BLOG_DIR + os.sep) and safe_path != BLOG_DIR:
        print("ERROR: unsafe file path generated, aborting.", file=sys.stderr)
        sys.exit(1)

    related_html = generate_related_articles_html(current_filename=filename)
    full_page = wrap_full_page(article_html, title, meta_description, related_html)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(full_page)

    print(f"Blog post written to: {safe_path}")

    # Regenerate the blog index so the new post is immediately listed.
    index_html = generate_index_html()
    index_path = os.path.join(BLOG_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"Blog index updated: {index_path}")


if __name__ == "__main__":
    main()
