"""Geo / region readiness assessment.

The user's goal is to rank organically **region-wise and country-wise**. Search
engines decide where to show a site using explicit geo-targeting signals. This
module checks which of those signals a page has and returns concrete,
white-hat recommendations for local / international SEO.

It never fabricates rankings — it measures readiness and prescribes the
legitimate steps that let Google serve the site to the right country/area.
"""

from __future__ import annotations

# Schema.org types that establish a physical / local business presence.
LOCAL_SCHEMA = {
    "LocalBusiness", "Store", "Restaurant", "Organization",
    "Corporation", "Place", "PostalAddress",
}


def assess_geo(onpage: dict, target_country: str | None = None) -> dict:
    """Assess geo-targeting readiness and produce region recommendations.

    ``onpage`` is the dict returned by :func:`trafficpilot.audit.onpage.analyze_html`.
    ``target_country`` (e.g. "BD", "US") is where the user wants to rank.
    """
    signals = {
        "html_lang": bool(onpage.get("lang")),
        "hreflang": onpage.get("has_hreflang", False),
        "local_business_schema": any(
            t in LOCAL_SCHEMA for t in onpage.get("schema_types", [])
        ),
        "https": onpage.get("https", False),
        "mobile_friendly": onpage.get("mobile_friendly", False),
    }
    score = round(sum(signals.values()) / len(signals) * 100, 1)

    recs: list[dict] = []

    if not signals["html_lang"]:
        recs.append(_r(
            "Set the page language",
            "Add a `lang` attribute to the <html> tag (e.g. `<html lang=\"en\">` or "
            "`lang=\"bn\"`). Google uses it to match the site to a language audience.",
            "High",
        ))
    if not signals["hreflang"] and target_country:
        recs.append(_r(
            "Add hreflang for country/language targeting",
            "Add `hreflang` alternate tags so Google serves the right version per "
            f"country/language (e.g. target '{target_country}'). This is the primary "
            "signal for region-wise organic ranking of multi-region sites.",
            "High",
        ))
    if not signals["local_business_schema"]:
        recs.append(_r(
            "Add LocalBusiness structured data",
            "Add JSON-LD `LocalBusiness` schema with your name, address (NAP), phone, "
            "opening hours and `areaServed`. This powers local/area-wise results and "
            "map packs.",
            "High" if target_country else "Medium",
        ))

    # Always-relevant local-SEO guidance (off-page, so advisory).
    recs.append(_r(
        "Claim & optimise Google Business Profile",
        "Create/verify a Google Business Profile with accurate categories, service "
        "areas and photos. This is the single biggest driver of area-wise (local-pack) "
        "visibility and is free.",
        "High",
        offsite=True,
    ))
    recs.append(_r(
        "Build local relevance & citations",
        "Publish location/area landing pages, earn links & consistent NAP citations "
        "from local directories, and collect genuine customer reviews. These are the "
        "legitimate signals that lift regional organic ranking over time.",
        "Medium",
        offsite=True,
    ))

    return {
        "readiness_score": score,
        "signals": signals,
        "target_country": target_country,
        "recommendations": recs,
    }


def _r(title: str, detail: str, priority: str, offsite: bool = False) -> dict:
    return {
        "title": title,
        "detail": detail,
        "category": "geo",
        "priority": priority,
        "expected_impact": "Better region/country-wise organic visibility",
        "offsite": offsite,
    }
