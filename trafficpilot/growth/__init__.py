"""Organic growth engine: shareability scoring, social content & distribution.

No tool can *force* a site to go viral. What this package does is maximise the
legitimate, white-hat levers of organic reach:

* :func:`score_virality` — measure how *shareable* a page is right now
* :func:`generate_social_kit` — ready-to-post captions + hashtags + OG/Twitter
  meta tags built from the page's real content
* :func:`distribution_plan` — a concrete organic-distribution checklist
"""

from trafficpilot.growth.virality import score_virality
from trafficpilot.growth.social import generate_social_kit, open_graph_tags
from trafficpilot.growth.distribution import distribution_plan
from trafficpilot.growth.engine import growth_report

__all__ = [
    "score_virality",
    "generate_social_kit",
    "open_graph_tags",
    "distribution_plan",
    "growth_report",
]
