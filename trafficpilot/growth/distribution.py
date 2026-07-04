"""Organic distribution playbook.

A prioritised, concrete checklist of legitimate ways to get a page in front of
people organically. Items adapt to what the page is already missing (e.g. it
only nags about Open Graph if the page lacks it). These are advisory actions —
the honest levers of organic reach, not automated posting or spam.
"""

from __future__ import annotations


def _step(action: str, detail: str, priority: str, channel: str) -> dict:
    return {"action": action, "detail": detail, "priority": priority, "channel": channel}


def distribution_plan(onpage: dict, virality: dict) -> list[dict]:
    steps: list[dict] = []

    # fix share previews first — everything shared depends on them
    if not onpage.get("open_graph") or not onpage.get("has_og_image"):
        steps.append(_step(
            "Fix the social share preview",
            "Add Open Graph + an og:image (1200×630). Until this exists, every "
            "share looks broken and gets ignored.",
            "High", "on-page"))

    steps.append(_step(
        "Publish natively to your social channels",
        "Post the page using the generated captions on Facebook, X, LinkedIn and "
        "Instagram. Post where your audience already is; be consistent (3–5×/week).",
        "High", "social"))

    steps.append(_step(
        "Answer real questions and link back",
        "Find questions your page answers on Reddit, Quora, Facebook Groups and "
        "niche forums; give a genuinely helpful reply and link where relevant. "
        "This drives targeted organic referral traffic.",
        "High", "community"))

    steps.append(_step(
        "Repurpose into short-form video",
        "Turn the key points into a 20–40s Reel / TikTok / YouTube Short. Short "
        "video is the fastest organic reach channel today.",
        "Medium", "video"))

    steps.append(_step(
        "Start an email capture + broadcast",
        "Add a newsletter signup and email new content to subscribers — owned "
        "distribution you fully control and that compounds over time.",
        "Medium", "email"))

    steps.append(_step(
        "Earn backlinks & mentions",
        "Do a guest post, get listed in relevant directories, or collaborate with "
        "a complementary site. Genuine links lift both referral traffic and "
        "search rankings.",
        "Medium", "off-site"))

    if virality.get("label") == "low":
        steps.append(_step(
            "Strengthen the content hook",
            "Shareability is low — sharpen the headline, add a compelling image and "
            "a clear takeaway before pushing distribution.",
            "High", "content"))

    order = {"High": 0, "Medium": 1, "Low": 2}
    steps.sort(key=lambda s: order.get(s["priority"], 3))
    return steps
