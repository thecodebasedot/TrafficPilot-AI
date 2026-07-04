"""Tests for the organic growth engine (virality, social kit, distribution)."""

from __future__ import annotations

from pathlib import Path

from trafficpilot.audit.keywords import extract_keywords
from trafficpilot.audit.onpage import analyze_html
from trafficpilot.growth import (
    distribution_plan,
    generate_social_kit,
    growth_report,
    open_graph_tags,
    score_virality,
)
from trafficpilot.growth.social import hashtags_from_keywords

HTML = (Path(__file__).parent / "fixtures" / "sample_store.html").read_text(encoding="utf-8")
URL = "https://example-store.test/"


def test_virality_score_bounds_and_components():
    op = analyze_html(HTML, URL)
    v = score_virality(op, extract_keywords(HTML))
    assert 0 <= v["score"] <= 100
    assert v["label"] in {"low", "medium", "high"}
    assert set(v["components"]) == {
        "headline_strength", "social_preview", "readability", "ease_of_sharing"
    }


def test_virality_rewards_social_preview():
    op = analyze_html(HTML, URL)
    kw = extract_keywords(HTML)
    without = dict(op, open_graph=False, has_og_image=False, has_twitter_card=False)
    with_preview = dict(op, open_graph=True, has_og_image=True, has_twitter_card=True)
    assert score_virality(with_preview, kw)["components"]["social_preview"] > \
        score_virality(without, kw)["components"]["social_preview"]


def test_hashtags_from_keywords():
    tags = hashtags_from_keywords(extract_keywords(HTML))
    assert all(t.startswith("#") for t in tags)
    assert any("leather" in t.lower() for t in tags)


def test_social_kit_has_all_platforms():
    kit = generate_social_kit("My Title", "A great description.", URL, extract_keywords(HTML))
    assert set(kit["posts"]) == {"facebook", "x", "linkedin", "instagram", "whatsapp"}
    # X post respects the length limit
    assert len(kit["posts"]["x"]) <= 280
    assert kit["posts"]["whatsapp"].startswith("*My Title*")


def test_open_graph_tags_are_wellformed():
    og = open_graph_tags("T", "D", URL)
    assert 'property="og:title"' in og
    assert 'name="twitter:card"' in og
    assert og.count("<meta") == 9


def test_open_graph_escapes_html():
    og = open_graph_tags('Bags & <Wallets>', "D", URL)
    assert "&amp;" in og and "&lt;" in og


def test_distribution_plan_prioritised():
    op = analyze_html(HTML, URL)
    v = score_virality(op, extract_keywords(HTML))
    plan = distribution_plan(op, v)
    order = {"High": 0, "Medium": 1, "Low": 2}
    prio = [order[s["priority"]] for s in plan]
    assert prio == sorted(prio)
    assert all({"action", "detail", "priority", "channel"} <= set(s) for s in plan)


def test_growth_report_assembles_everything():
    op = analyze_html(HTML, URL)
    report = growth_report(op, extract_keywords(HTML), URL)
    assert {"virality", "social_kit", "open_graph_tags", "distribution_plan"} <= set(report)
    assert report["distribution_plan"]
