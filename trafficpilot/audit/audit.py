"""Orchestrate a full real-website audit.

``audit_site(url)`` crawls a live URL and returns a :class:`SiteAudit` with:

* measured on-page & technical SEO signals
* a real (measured-only) SEO score + letter grade
* index-status assessment from robots.txt / sitemap.xml / meta-robots
* extracted keywords the page currently targets
* geo/region readiness + local-SEO recommendations
* a prioritised, actionable recommendation list

Signals that require third-party data (domain authority, backlink counts, exact
SERP rank) are **not** fabricated — they are reported as "needs external API".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from trafficpilot.audit.fetch import fetch, fetch_robots, fetch_sitemap
from trafficpilot.audit.geo import assess_geo
from trafficpilot.audit.keywords import extract_keywords
from trafficpilot.audit.onpage import analyze_html
from trafficpilot.config import GOOD_PAGE_SPEED
from trafficpilot.growth import growth_report


# --------------------------------------------------------------------------- #
# Real, measured-only on-page SEO score
# --------------------------------------------------------------------------- #
def score_onpage(onpage: dict, elapsed: float) -> dict:
    """Compute an SEO score purely from measured on-page/technical signals."""
    c = {}
    c["title"] = 100.0 if onpage["title_ok"] else (60.0 if onpage["title"] else 0.0)
    c["meta_description"] = 100.0 if onpage["description_ok"] else (55.0 if onpage["description"] else 0.0)
    c["headings"] = 100.0 if onpage["h1_count"] == 1 else (50.0 if onpage["h1_count"] else 0.0)
    c["content_depth"] = float(np.clip(onpage["word_count"] / 800 * 100, 0, 100))
    c["mobile_friendly"] = 100.0 if onpage["mobile_friendly"] else 20.0
    c["https"] = 100.0 if onpage["https"] else 0.0
    c["canonical"] = 100.0 if onpage["has_canonical"] else 50.0
    c["structured_data"] = 100.0 if onpage["has_structured_data"] else 40.0
    c["image_alt"] = 100.0 if onpage["images"] == 0 else float(
        np.clip((1 - onpage["images_missing_alt"] / max(onpage["images"], 1)) * 100, 0, 100)
    )
    c["page_speed"] = float(np.clip(100 - (elapsed - GOOD_PAGE_SPEED) * 20, 0, 100))

    weights = {
        "title": 0.14, "meta_description": 0.10, "headings": 0.10,
        "content_depth": 0.12, "mobile_friendly": 0.12, "https": 0.10,
        "canonical": 0.07, "structured_data": 0.09, "image_alt": 0.06,
        "page_speed": 0.10,
    }
    overall = round(sum(c[k] * weights[k] for k in c), 1)
    return {
        "components": {k: round(v, 1) for k, v in c.items()},
        "weights": weights,
        "overall": overall,
        "grade": _grade(overall),
    }


def _grade(score: float) -> str:
    for thr, g in [(90, "A"), (80, "B"), (70, "C"), (55, "D")]:
        if score >= thr:
            return g
    return "F"


def index_status(onpage: dict, robots: dict, sitemap: dict) -> dict:
    """Assess whether the page is set up to be indexed by Google."""
    warnings = []
    if onpage["noindex"]:
        warnings.append("Page has a `noindex` meta robots tag — Google will NOT index it.")
    if robots.get("blocks_all"):
        warnings.append("robots.txt disallows all crawlers (`Disallow: /`).")
    if not robots.get("present"):
        warnings.append("No robots.txt found — add one and reference your sitemap.")
    if not sitemap.get("present"):
        warnings.append("No XML sitemap found — add /sitemap.xml and submit it in Search Console.")
    if not onpage["https"]:
        warnings.append("Site is not served over HTTPS — a ranking and trust negative.")

    indexable = not onpage["noindex"] and not robots.get("blocks_all")
    return {
        "indexable": indexable,
        "robots_present": robots.get("present", False),
        "sitemap_present": sitemap.get("present", False),
        "sitemap_url_count": sitemap.get("url_count", 0),
        "status": "ready to index" if indexable and sitemap.get("present") else "needs attention",
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# Recommendation building from measured issues
# --------------------------------------------------------------------------- #
def _rec(title, detail, category, priority, impact):
    return {"title": title, "detail": detail, "category": category,
            "priority": priority, "expected_impact": impact}


def build_recommendations(onpage: dict, seo: dict, idx: dict, geo: dict) -> list[dict]:
    recs: list[dict] = []

    if not onpage["title_ok"]:
        recs.append(_rec(
            "Fix the page title",
            f"Title is {onpage['title_length']} chars; keep it 30–60 and lead with the "
            "primary keyword.", "seo", "High", "Higher click-through & rankings"))
    if not onpage["description_ok"]:
        recs.append(_rec(
            "Write a compelling meta description",
            f"Description is {onpage['description_length']} chars; write a 70–160-char "
            "summary with the keyword and a call to action.", "seo", "Medium",
            "Higher click-through from search"))
    if onpage["h1_count"] != 1:
        recs.append(_rec(
            "Use exactly one H1",
            f"Found {onpage['h1_count']} H1 tags. Use a single, keyword-rich H1 per page.",
            "seo", "Medium", "Clearer topical relevance"))
    if onpage["word_count"] < 300:
        recs.append(_rec(
            "Add more useful content",
            f"Only ~{onpage['word_count']} words. Thin pages rank poorly — aim for "
            "in-depth, genuinely helpful content.", "content", "High",
            "More keywords & organic traffic"))
    if onpage["images"] and onpage["images_missing_alt"]:
        recs.append(_rec(
            "Add alt text to images",
            f"{onpage['images_missing_alt']} of {onpage['images']} images lack alt text. "
            "Describe them for accessibility and image search.", "seo", "Low",
            "Image-search traffic & accessibility"))
    if not onpage["has_structured_data"]:
        recs.append(_rec(
            "Add structured data (schema.org)",
            "Add JSON-LD (Product, Article, Breadcrumb, etc.) to earn rich results and "
            "help Google understand the page.", "seo", "Medium", "Rich results in SERPs"))
    if not onpage["mobile_friendly"]:
        recs.append(_rec(
            "Make the page mobile-friendly",
            "No viewport meta tag found. Use a responsive layout — Google indexes "
            "mobile-first.", "seo", "High", "Avoids mobile ranking penalties"))
    if seo["components"]["page_speed"] < 70:
        recs.append(_rec(
            "Improve page speed",
            "The page responded slowly. Compress images, cache, and minimise JS/CSS.",
            "speed", "High", "Lower bounce, better crawl & rankings"))

    for w in idx["warnings"]:
        recs.append(_rec("Fix indexing blocker", w, "indexing", "High", "Gets the page indexed"))

    recs.extend(geo["recommendations"])

    order = {"High": 0, "Medium": 1, "Low": 2}
    recs.sort(key=lambda r: order.get(r["priority"], 3))
    return recs


@dataclass
class SiteAudit:
    url: str
    ok: bool
    error: str | None = None
    fetch_info: dict = field(default_factory=dict)
    onpage: dict = field(default_factory=dict)
    seo_score: dict = field(default_factory=dict)
    index_status: dict = field(default_factory=dict)
    keywords: dict = field(default_factory=dict)
    geo: dict = field(default_factory=dict)
    growth: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "url": self.url, "ok": self.ok, "error": self.error,
            "fetch_info": self.fetch_info, "onpage": self.onpage,
            "seo_score": self.seo_score, "index_status": self.index_status,
            "keywords": self.keywords, "geo": self.geo, "growth": self.growth,
            "recommendations": self.recommendations, "notes": self.notes,
        }


def audit_site(url: str, target_country: str | None = None) -> SiteAudit:
    """Run the full audit for ``url``; returns a :class:`SiteAudit`."""
    res = fetch(url)
    if not res.ok or not res.html:
        return SiteAudit(
            url=url, ok=False,
            error=res.error or f"HTTP {res.status} or non-HTML response",
            fetch_info={"status": res.status, "final_url": res.final_url},
        )

    onpage = analyze_html(res.html, res.final_url, res.headers)
    robots = fetch_robots(res.final_url)
    sitemap = fetch_sitemap(res.final_url, robots)

    seo = score_onpage(onpage, res.elapsed)
    idx = index_status(onpage, robots, sitemap)
    kw = extract_keywords(res.html)
    geo = assess_geo(onpage, target_country)
    growth = growth_report(onpage, kw, res.final_url)
    recs = build_recommendations(onpage, seo, idx, geo)

    notes = [
        "Domain authority, backlink count and exact keyword SERP rank require a "
        "third-party API (Moz / Ahrefs / SEMrush) and are not measured here.",
        "Traffic & sales forecasts need your historical analytics — connect Google "
        "Analytics to enable the ML forecast for this site.",
    ]

    return SiteAudit(
        url=res.final_url, ok=True,
        fetch_info={
            "status": res.status, "final_url": res.final_url,
            "response_time_s": res.elapsed, "https": onpage["https"],
        },
        onpage=onpage, seo_score=seo, index_status=idx,
        keywords=kw, geo=geo, growth=growth, recommendations=recs, notes=notes,
    )
