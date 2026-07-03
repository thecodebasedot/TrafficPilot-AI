"""On-page & technical SEO extraction from fetched HTML.

Parses a page with BeautifulSoup and measures the concrete signals search
engines care about: title, meta description, headings, word count, images with
missing alt text, internal/external links, canonical, viewport (mobile),
language, hreflang, Open Graph and JSON-LD structured data.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Sensible SEO length targets used for pass/fail flags.
TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 70, 160


def _text_words(soup: BeautifulSoup) -> int:
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(" ", strip=True)
    return len(re.findall(r"\w+", text))


def analyze_html(html: str, final_url: str, headers: dict | None = None) -> dict:
    """Return a dict of on-page/technical SEO signals for the page."""
    headers = headers or {}
    soup = BeautifulSoup(html or "", "html.parser")
    host = urlparse(final_url).netloc

    # --- title & meta description ------------------------------------- #
    title = (soup.title.string or "").strip() if soup.title else ""
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = (desc_tag.get("content", "").strip() if desc_tag else "")

    # --- headings ----------------------------------------------------- #
    h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2 = soup.find_all("h2")

    # --- images / alt ------------------------------------------------- #
    imgs = soup.find_all("img")
    imgs_missing_alt = sum(1 for i in imgs if not i.get("alt", "").strip())

    # --- links -------------------------------------------------------- #
    internal, external = 0, 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        netloc = urlparse(urljoin(final_url, href)).netloc
        if netloc == host or not netloc:
            internal += 1
        else:
            external += 1

    # --- technical signals -------------------------------------------- #
    canonical_tag = soup.find("link", rel=lambda v: v and "canonical" in v)
    canonical = canonical_tag.get("href") if canonical_tag else None

    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    mobile_friendly = bool(viewport)

    html_tag = soup.find("html")
    lang = html_tag.get("lang") if html_tag else None

    hreflangs = [
        l.get("hreflang")
        for l in soup.find_all("link", rel=lambda v: v and "alternate" in v)
        if l.get("hreflang")
    ]

    robots_meta = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    robots_content = (robots_meta.get("content", "").lower() if robots_meta else "")
    noindex = "noindex" in robots_content

    og_tags = {
        m.get("property"): m.get("content")
        for m in soup.find_all("meta", property=re.compile("^og:", re.I))
    }

    # --- structured data (JSON-LD) ------------------------------------ #
    schema_types = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (ValueError, TypeError):
            continue
        for obj in data if isinstance(data, list) else [data]:
            if isinstance(obj, dict) and obj.get("@type"):
                t = obj["@type"]
                schema_types.extend(t if isinstance(t, list) else [t])

    words = _text_words(soup)

    return {
        "title": title,
        "title_length": len(title),
        "title_ok": TITLE_MIN <= len(title) <= TITLE_MAX,
        "description": description,
        "description_length": len(description),
        "description_ok": DESC_MIN <= len(description) <= DESC_MAX,
        "h1": h1,
        "h1_count": len(h1),
        "h2_count": len(h2),
        "word_count": words,
        "images": len(imgs),
        "images_missing_alt": imgs_missing_alt,
        "internal_links": internal,
        "external_links": external,
        "canonical": canonical,
        "has_canonical": canonical is not None,
        "mobile_friendly": mobile_friendly,
        "lang": lang,
        "hreflang": hreflangs,
        "has_hreflang": bool(hreflangs),
        "noindex": noindex,
        "https": urlparse(final_url).scheme == "https",
        "open_graph": bool(og_tags),
        "schema_types": sorted(set(schema_types)),
        "has_structured_data": bool(schema_types),
        "is_https": urlparse(final_url).scheme == "https",
        "last_modified": headers.get("Last-Modified"),
    }
