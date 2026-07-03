"""K-Means visitor segmentation.

Groups visitors into behavioural segments (e.g. loyal high-value, casual
browsers, one-off bargain hunters) and produces a human-readable profile for
each cluster so marketers can target them differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from trafficpilot.config import (
    ARTIFACTS_DIR,
    DEFAULT_N_SEGMENTS,
    RANDOM_STATE,
    VISITOR_FEATURES,
)


@dataclass
class VisitorSegmenter:
    """Cluster visitors into behavioural segments with K-Means."""

    n_segments: int = DEFAULT_N_SEGMENTS
    feature_columns: list[str] = field(default_factory=lambda: list(VISITOR_FEATURES))
    scaler: StandardScaler | None = None
    model: KMeans | None = None
    silhouette: float | None = None
    labels_: dict[int, str] = field(default_factory=dict)

    def fit(self, df: pd.DataFrame) -> "VisitorSegmenter":
        X = df[self.feature_columns]
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)
        self.model = KMeans(
            n_clusters=self.n_segments, random_state=RANDOM_STATE, n_init=10
        )
        clusters = self.model.fit_predict(Xs)
        if len(set(clusters)) > 1:
            self.silhouette = float(silhouette_score(Xs, clusters))
        self._name_segments(df.assign(segment=clusters))
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.model is None or self.scaler is None:
            raise RuntimeError("Segmenter is not trained. Call fit() first.")
        return self.model.predict(self.scaler.transform(df[self.feature_columns]))

    def _name_segments(self, df: pd.DataFrame) -> None:
        """Assign a descriptive label to each cluster from its centroid profile."""
        profile = df.groupby("segment")[self.feature_columns].mean()
        spend_rank = profile["total_spend"].rank(ascending=False)
        for seg in profile.index:
            spend = profile.loc[seg, "total_spend"]
            sessions = profile.loc[seg, "sessions"]
            recency = profile.loc[seg, "recency_days"]
            if spend_rank[seg] == 1 and sessions >= profile["sessions"].median():
                name = "Loyal high-value"
            elif recency > profile["recency_days"].median() and sessions < 2.5:
                name = "One-off / at-risk"
            elif sessions >= profile["sessions"].median():
                name = "Engaged browsers"
            else:
                name = "Casual visitors"
            self.labels_[int(seg)] = name

    def profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a per-segment summary table (size, label, centroid means)."""
        clusters = self.predict(df)
        enriched = df.assign(segment=clusters)
        summary = enriched.groupby("segment")[self.feature_columns].mean().round(1)
        summary.insert(0, "label", [self.labels_.get(int(s), f"Segment {s}") for s in summary.index])
        summary.insert(1, "visitors", enriched.groupby("segment").size())
        summary["share_pct"] = (summary["visitors"] / len(df) * 100).round(1)
        return summary.reset_index()

    # ------------------------------------------------------------------ #
    def save(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path else ARTIFACTS_DIR / "segmenter.joblib"
        joblib.dump(
            {
                "n_segments": self.n_segments,
                "feature_columns": self.feature_columns,
                "scaler": self.scaler,
                "model": self.model,
                "silhouette": self.silhouette,
                "labels_": self.labels_,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "VisitorSegmenter":
        path = Path(path) if path else ARTIFACTS_DIR / "segmenter.joblib"
        blob = joblib.load(path)
        obj = cls(n_segments=blob["n_segments"], feature_columns=blob["feature_columns"])
        obj.scaler = blob["scaler"]
        obj.model = blob["model"]
        obj.silhouette = blob["silhouette"]
        obj.labels_ = blob["labels_"]
        return obj
