from trafficpilot.config import FEATURE_COLUMNS, TARGETS, VISITOR_FEATURES
from trafficpilot.data import (
    generate_competitors,
    generate_keywords,
    generate_site_metrics,
    generate_visitors,
)


def test_site_metrics_shape_and_columns():
    df = generate_site_metrics(n_days=120, seed=1)
    assert len(df) == 120
    for col in FEATURE_COLUMNS + TARGETS:
        assert col in df.columns


def test_site_metrics_are_reproducible():
    a = generate_site_metrics(n_days=50, seed=7)
    b = generate_site_metrics(n_days=50, seed=7)
    assert a.equals(b)


def test_site_metrics_value_ranges():
    df = generate_site_metrics(n_days=200, seed=2)
    assert df["bounce_rate"].between(0, 100).all()
    assert df["conversion_rate"].between(0, 100).all()
    assert (df["sales"] >= 0).all()
    assert df["seo_score"].between(0, 100).all()


def test_visitors_have_features():
    v = generate_visitors(n_visitors=300, seed=3)
    assert len(v) == 300
    for col in VISITOR_FEATURES:
        assert col in v.columns


def test_keywords_and_competitors():
    kw = generate_keywords(n_keywords=25, seed=4)
    assert {"keyword", "search_volume", "current_rank", "difficulty"}.issubset(kw.columns)
    comp = generate_competitors(seed=4)
    assert "Your Site" in set(comp["site"])
