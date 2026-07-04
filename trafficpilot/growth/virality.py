"""Shareability / virality-readiness scoring.

Virality can't be forced, but *shareability* is measurable. Pages that get
shared organically tend to: have a strong, specific headline; render a rich
social preview (Open Graph / Twitter card + image); be readable and skimmable;
carry an emotional or curiosity hook; and make sharing easy. This module scores
those concrete signals from a page and returns component sub-scores + fixes.
"""

from __future__ import annotations

import re

import numpy as np

# Words that reliably lift headline click / share rates (kept small & honest).
POWER_WORDS = {
    "how", "why", "best", "top", "guide", "easy", "free", "new", "proven",
    "ultimate", "secret", "mistakes", "tips", "results", "fast", "simple",
    "essential", "checklist", "step", "steps", "beginner", "expert", "review",
}
EMOTION_WORDS = {
    "amazing", "surprising", "shocking", "love", "hate", "fear", "incredible",
    "unbelievable", "powerful", "beautiful", "worst", "smart", "genius",
}


def _headline_strength(title: str) -> tuple[float, list[str]]:
    tips = []
    if not title:
        return 0.0, ["Add a page title / headline."]
    score = 40.0
    words = re.findall(r"[a-zA-Z]+", title.lower())

    if any(w in POWER_WORDS for w in words):
        score += 20
    else:
        tips.append("Add a power word (how, best, guide, tips, checklist…) to the headline.")

    if any(w in EMOTION_WORDS for w in words):
        score += 15
    else:
        tips.append("Consider an emotional or curiosity hook in the headline.")

    if re.search(r"\d", title):
        score += 15
    else:
        tips.append("Numbers ('7 ways…') make headlines more clickable & shareable.")

    if "?" in title or title.lower().startswith(("how", "why", "what")):
        score += 10

    return float(np.clip(score, 0, 100)), tips


def score_virality(onpage: dict, keywords: dict | None = None) -> dict:
    """Return a shareability score (0-100) with component breakdown and fixes."""
    fixes: list[str] = []
    headline, htips = _headline_strength(onpage.get("title", ""))
    fixes.extend(htips)

    # social preview readiness
    preview = 0.0
    if onpage.get("open_graph"):
        preview += 45
    else:
        fixes.append("Add Open Graph tags so shared links show a rich preview card.")
    if onpage.get("has_og_image"):
        preview += 35
    else:
        fixes.append("Add an `og:image` (1200×630) — posts with images get far more shares.")
    if onpage.get("has_twitter_card"):
        preview += 20
    else:
        fixes.append("Add Twitter Card tags for better previews on X.")

    # readability / skimmability
    words = onpage.get("word_count", 0)
    read = float(np.clip((words / 600) * 60, 0, 60)) if words < 600 else 60.0
    read += 20 if onpage.get("h2_count", 0) >= 2 else 0
    read += 20 if onpage.get("images", 0) >= 1 else 0
    read = float(np.clip(read, 0, 100))
    if onpage.get("h2_count", 0) < 2:
        fixes.append("Break content into sections with H2 subheadings for skimmability.")

    # ease of sharing
    share = 60.0 if onpage.get("social_links") else 20.0
    if not onpage.get("social_links"):
        fixes.append("Add social share / follow buttons so readers can spread it in one tap.")
    share = float(np.clip(share + (20 if onpage.get("mobile_friendly") else 0), 0, 100))

    components = {
        "headline_strength": round(headline, 1),
        "social_preview": round(preview, 1),
        "readability": round(read, 1),
        "ease_of_sharing": round(share, 1),
    }
    weights = {
        "headline_strength": 0.30,
        "social_preview": 0.30,
        "readability": 0.20,
        "ease_of_sharing": 0.20,
    }
    overall = round(sum(components[k] * weights[k] for k in components), 1)
    label = (
        "high" if overall >= 75 else "medium" if overall >= 50 else "low"
    )
    return {
        "score": overall,
        "label": label,
        "components": components,
        "weights": weights,
        "fixes": fixes,
    }
