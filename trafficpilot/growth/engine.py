"""Assemble the full growth report from a page's audit signals."""

from __future__ import annotations

from trafficpilot.growth.distribution import distribution_plan
from trafficpilot.growth.social import generate_social_kit, open_graph_tags
from trafficpilot.growth.virality import score_virality


def growth_report(onpage: dict, keywords: dict, url: str) -> dict:
    """Combine shareability, social kit, OG tags and distribution plan."""
    virality = score_virality(onpage, keywords)
    social = generate_social_kit(
        onpage.get("title", ""), onpage.get("description", ""), url, keywords
    )
    og = open_graph_tags(
        onpage.get("title", ""), onpage.get("description", ""), url
    )
    plan = distribution_plan(onpage, virality)
    return {
        "virality": virality,
        "social_kit": social,
        "open_graph_tags": og,
        "distribution_plan": plan,
    }
