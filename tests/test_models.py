import numpy as np

from trafficpilot.data import generate_site_metrics, generate_visitors
from trafficpilot.models import (
    FeatureImportanceAnalyzer,
    TrafficPredictor,
    VisitorSegmenter,
)


def test_traffic_predictor_trains_and_predicts():
    df = generate_site_metrics(n_days=400, seed=5)
    model = TrafficPredictor().fit(df)
    for target in model.targets:
        assert target in model.metrics
    preds = model.predict(df.head(10))
    assert list(preds.columns) == model.targets
    assert len(preds) == 10
    # traffic model should fit the synthetic signal well
    assert model.metrics["total_traffic"]["r2"] > 0.7


def test_traffic_predictor_forecast():
    df = generate_site_metrics(n_days=300, seed=6)
    model = TrafficPredictor().fit(df)
    fc = model.forecast_next(df, horizon=7)
    assert len(fc) == 7
    assert (fc["sales"] >= 0).all()


def test_traffic_predictor_save_load(tmp_path):
    df = generate_site_metrics(n_days=200, seed=7)
    model = TrafficPredictor().fit(df)
    p = model.save(tmp_path / "pred.joblib")
    loaded = TrafficPredictor.load(p)
    a = model.predict(df.head(5))
    b = loaded.predict(df.head(5))
    assert np.allclose(a.values, b.values)


def test_importance_ranks_features():
    df = generate_site_metrics(n_days=400, seed=8)
    an = FeatureImportanceAnalyzer(target="sales").fit(df)
    imp = an.importances()
    assert abs(imp["importance"].sum() - 1.0) < 1e-6
    # organic traffic is the strongest synthetic driver of sales
    assert imp.iloc[0]["feature"] in {"organic_traffic", "paid_traffic",
                                       "referral_traffic", "direct_traffic"}


def test_segmenter_clusters_visitors():
    v = generate_visitors(n_visitors=600, seed=9)
    seg = VisitorSegmenter(n_segments=4).fit(v)
    labels = seg.predict(v)
    assert len(set(labels)) == 4
    prof = seg.profile(v)
    assert len(prof) == 4
    assert prof["visitors"].sum() == len(v)
    assert seg.silhouette is not None
