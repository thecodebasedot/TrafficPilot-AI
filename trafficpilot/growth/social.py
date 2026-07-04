"""Generate ready-to-post social content and share meta tags.

Everything here is derived from the page's own real content (title, description,
extracted keywords) — no fabricated claims. The output is copy-paste ready:

* per-platform captions (Facebook, X/Twitter, LinkedIn, Instagram, WhatsApp)
* hashtags derived from the page's top keywords
* Open Graph + Twitter Card meta tags to drop into the page ``<head>``
"""

from __future__ import annotations

import re
from html import escape


def _hashtagify(term: str) -> str:
    parts = re.findall(r"[a-zA-Z0-9]+", term)
    return "#" + "".join(p.capitalize() for p in parts) if parts else ""


def hashtags_from_keywords(keywords: dict, limit: int = 8) -> list[str]:
    """Build hashtags from the page's top unigrams/bigrams."""
    terms = []
    for b in (keywords or {}).get("bigrams", []):
        terms.append(b["term"])
    for u in (keywords or {}).get("unigrams", []):
        terms.append(u["term"])
    tags, seen = [], set()
    for t in terms:
        tag = _hashtagify(t)
        key = tag.lower()
        if tag and key not in seen and len(tag) > 2:
            seen.add(key)
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


def generate_social_kit(title: str, description: str, url: str, keywords: dict) -> dict:
    """Return per-platform post copy + hashtags for a page."""
    title = (title or "").strip() or "Check this out"
    description = (description or "").strip()
    tags = hashtags_from_keywords(keywords)
    tag_line = " ".join(tags)
    short_tags = " ".join(tags[:3])
    hook = description or title

    posts = {
        "facebook": f"{title}\n\n{hook}\n\n👉 {url}\n\n{tag_line}".strip(),
        "x": _truncate(f"{title} — {url} {short_tags}", 270),
        "linkedin": (
            f"{title}\n\n{hook}\n\nRead more: {url}\n\n{tag_line}"
        ).strip(),
        "instagram": f"{title} ✨\n\n{hook}\n\nLink in bio 🔗\n\n{tag_line}".strip(),
        "whatsapp": f"*{title}*\n{hook}\n{url}".strip(),
    }
    return {"hashtags": tags, "posts": posts}


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def open_graph_tags(title: str, description: str, url: str, image: str | None = None) -> str:
    """Return copy-paste Open Graph + Twitter Card <meta> tags for the page."""
    title = escape((title or "").strip())
    description = escape((description or "").strip())
    url = escape(url or "")
    image = escape(image or f"{url.rstrip('/')}/og-image.jpg")
    return "\n".join([
        f'<meta property="og:title" content="{title}" />',
        f'<meta property="og:description" content="{description}" />',
        f'<meta property="og:url" content="{url}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:image" content="{image}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{title}" />',
        f'<meta name="twitter:description" content="{description}" />',
        f'<meta name="twitter:image" content="{image}" />',
    ])
