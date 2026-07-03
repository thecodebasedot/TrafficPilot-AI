"""High-level service that assembles the full analytics payload.

This is the bridge between the trained models / analysis helpers and any
front-end (the Flask dashboard or a future API client). It loads artifacts if
they exist, otherwise trains them on demand, and exposes a single
:meth:`TrafficPilotService.dashboard` method returning everything the UI needs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trafficpilot.analysis import (
    RecommendationEngine,
    competitor_comparison,
    google_index_status,
    keyword_opportunities,
    seo_score_breakdown,
)
from trafficpilot.audit import audit_site
from trafficpilot.config import ARTIFACTS_DIR
from trafficpilot.data import (
    generate_competitors,
    generate_keywords,
    generate_site_metrics,
    generate_visitors,
)
from trafficpilot.models import (
    FeatureImportanceAnalyzer,
    TrafficPredictor,
    VisitorSegmenter,
)


class TrafficPilotService:
    """Loads models + data and builds the dashboard payload."""

    def __init__(self, auto_train: bool = True):
        self.site = generate_site_metrics()
        self.visitors = generate_visitors()
        self.keywords = generate_keywords()
        self.competitors = generate_competitors()

        if self._artifacts_exist():
            self.predictor = TrafficPredictor.load()
            self.analyzer = FeatureImportanceAnalyzer.load()
            self.segmenter = VisitorSegmenter.load()
        elif auto_train:
            self.predictor = TrafficPredictor().fit(self.site)
            self.analyzer = FeatureImportanceAnalyzer(target="sales").fit(self.site)
            self.segmenter = VisitorSegmenter().fit(self.visitors)
        else:
            raise RuntimeError(
                "No trained artifacts found. Run `python -m trafficpilot.train` first."
            )

        self.recommender = RecommendationEngine(self.analyzer.importances())

    @staticmethod
    def _artifacts_exist() -> bool:
        return all(
            (ARTIFACTS_DIR / name).exists()
            for name in ("traffic_predictor.joblib", "importance.joblib", "segmenter.joblib")
        )

    # ------------------------------------------------------------------ #
    def latest_metrics(self) -> dict:
        """Most recent day's metrics as a plain dict."""
        row = self.site.iloc[-1]
        return {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v)
                for k, v in row.drop("date").items()}

    def kpis(self) -> dict:
        """Headline dashboard KPIs with period-over-period deltas."""
        last = self.site.iloc[-1]
        prev = self.site.iloc[-8]  # a week earlier

        def delta(col):
            if prev[col] == 0:
                return 0.0
            return round((last[col] - prev[col]) / prev[col] * 100, 1)

        # a small "live visitors" estimate from the latest day
        live = int(last["total_traffic"] / (24 * 12))  # per 5-min slot

        return {
            "live_visitors": max(live, 1),
            "total_traffic": {"value": int(last["total_traffic"]), "delta": delta("total_traffic")},
            "organic_traffic": {"value": int(last["organic_traffic"]), "delta": delta("organic_traffic")},
            "paid_traffic": {"value": int(last["paid_traffic"]), "delta": delta("paid_traffic")},
            "referral_traffic": {"value": int(last["referral_traffic"]), "delta": delta("referral_traffic")},
            "direct_traffic": {"value": int(last["direct_traffic"]), "delta": delta("direct_traffic")},
            "conversion_rate": {"value": round(float(last["conversion_rate"]), 2), "delta": delta("conversion_rate")},
            "bounce_rate": {"value": round(float(last["bounce_rate"]), 1), "delta": delta("bounce_rate")},
            "page_speed": {"value": round(float(last["page_speed"]), 2), "delta": delta("page_speed")},
            "avg_keyword_rank": {"value": round(float(last["keyword_rank_avg"]), 1), "delta": delta("keyword_rank_avg")},
        }

    def traffic_series(self, days: int = 60) -> dict:
        """Traffic-channel time series for charting."""
        tail = self.site.tail(days)
        return {
            "dates": tail["date"].dt.strftime("%Y-%m-%d").tolist(),
            "organic": tail["organic_traffic"].astype(int).tolist(),
            "paid": tail["paid_traffic"].astype(int).tolist(),
            "referral": tail["referral_traffic"].astype(int).tolist(),
            "direct": tail["direct_traffic"].astype(int).tolist(),
        }

    def sales_forecast(self, horizon: int = 14) -> dict:
        """Historic sales plus a forward forecast."""
        hist = self.site.tail(30)
        fc = self.predictor.forecast_next(self.site, horizon=horizon)
        return {
            "history_dates": hist["date"].dt.strftime("%Y-%m-%d").tolist(),
            "history_sales": hist["sales"].round(0).tolist(),
            "forecast_days": fc["day"].tolist(),
            "forecast_sales": fc["sales"].round(0).tolist(),
            "forecast_traffic": fc["total_traffic"].round(0).tolist(),
        }

    def segments(self) -> list[dict]:
        prof = self.segmenter.profile(self.visitors)
        return prof.to_dict(orient="records")

    def seo(self) -> dict:
        m = self.latest_metrics()
        return {
            "breakdown": seo_score_breakdown(m),
            "index_status": google_index_status(m),
        }

    def keyword_table(self, top_n: int = 10) -> list[dict]:
        opps = keyword_opportunities(self.keywords, top_n=top_n)
        opps["priority"] = opps["priority"].astype(str)
        return opps.to_dict(orient="records")

    def competitors_view(self) -> dict:
        return competitor_comparison(self.competitors)

    def drivers(self, n: int = 6) -> list[dict]:
        return self.analyzer.top_drivers(n)

    def recommendations(self) -> list[dict]:
        m = self.latest_metrics()
        return self.recommender.generate_dicts(m, self.keywords)

    def model_metrics(self) -> dict:
        return {
            "predictor": self.predictor.metrics,
            "importance_r2": self.analyzer.r2,
            "segmenter_silhouette": self.segmenter.silhouette,
        }

    # ------------------------------------------------------------------ #
    def audit(self, url: str, target_country: str | None = None) -> dict:
        """Run a real-website audit for ``url`` and return it as a dict."""
        return audit_site(url, target_country=target_country).as_dict()

    # ------------------------------------------------------------------ #
    def dashboard(self) -> dict:
        """The single payload consumed by the front-end."""
        return {
            "kpis": self.kpis(),
            "traffic_series": self.traffic_series(),
            "sales_forecast": self.sales_forecast(),
            "segments": self.segments(),
            "seo": self.seo(),
            "keywords": self.keyword_table(),
            "competitors": self.competitors_view(),
            "drivers": self.drivers(),
            "recommendations": self.recommendations(),
            "model_metrics": self.model_metrics(),
        }
