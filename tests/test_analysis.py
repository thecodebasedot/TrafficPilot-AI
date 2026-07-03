from trafficpilot.analysis import (
    RecommendationEngine,
    competitor_comparison,
    google_index_status,
    keyword_opportunities,
    seo_score_breakdown,
)
from trafficpilot.data import generate_competitors, generate_keywords


def test_seo_breakdown_bounds():
    metrics = {
        "page_speed": 3.5, "domain_authority": 40, "keyword_rank_avg": 20,
        "content_freshness_days": 30, "mobile_friendly": 1, "backlinks": 800,
        "seo_score": 60,
    }
    b = seo_score_breakdown(metrics)
    assert 0 <= b["overall"] <= 100
    assert b["grade"] in {"A", "B", "C", "D", "F"}
    for v in b["components"].values():
        assert 0 <= v <= 100


def test_seo_grade_improves_with_better_metrics():
    weak = seo_score_breakdown({"page_speed": 7, "domain_authority": 10,
                                "keyword_rank_avg": 60, "content_freshness_days": 200,
                                "mobile_friendly": 0, "backlinks": 20})
    strong = seo_score_breakdown({"page_speed": 1.5, "domain_authority": 80,
                                  "keyword_rank_avg": 3, "content_freshness_days": 5,
                                  "mobile_friendly": 1, "backlinks": 50000})
    assert strong["overall"] > weak["overall"]


def test_index_status_flags_problems():
    good = google_index_status({"indexed_pages": 1500, "page_speed": 2.0,
                                "mobile_friendly": 1, "seo_score": 80})
    bad = google_index_status({"indexed_pages": 10, "page_speed": 8.0,
                               "mobile_friendly": 0, "seo_score": 20})
    assert good["status"] == "healthy"
    assert bad["status"] == "needs attention"
    assert bad["warnings"]


def test_keyword_opportunities_scored_and_sorted():
    kw = generate_keywords(n_keywords=30, seed=1)
    opps = keyword_opportunities(kw, top_n=8)
    assert len(opps) == 8
    assert opps["opportunity"].is_monotonic_decreasing
    assert set(opps["priority"].astype(str)).issubset({"Low", "Medium", "High"})


def test_competitor_comparison_structure():
    comp = generate_competitors(seed=1)
    out = competitor_comparison(comp)
    assert "your_ranks" in out and "gaps" in out
    assert out["n_sites"] == len(comp)


def test_recommendations_prioritised():
    metrics = {
        "page_speed": 6.0, "seo_score": 40, "content_freshness_days": 150,
        "bounce_rate": 70, "mobile_friendly": 0, "domain_authority": 20,
        "keyword_rank_avg": 40, "backlinks": 100,
    }
    kw = generate_keywords(n_keywords=20, seed=2)
    recs = RecommendationEngine().generate_dicts(metrics, kw)
    assert recs, "expected recommendations for a poorly performing site"
    order = {"High": 0, "Medium": 1, "Low": 2}
    prio = [order[r["priority"]] for r in recs]
    assert prio == sorted(prio)
    # a healthy site should yield fewer recommendations
    healthy = {
        "page_speed": 1.8, "seo_score": 90, "content_freshness_days": 10,
        "bounce_rate": 35, "mobile_friendly": 1, "domain_authority": 70,
        "keyword_rank_avg": 5, "backlinks": 40000,
    }
    assert len(RecommendationEngine().generate_dicts(healthy)) < len(recs)
