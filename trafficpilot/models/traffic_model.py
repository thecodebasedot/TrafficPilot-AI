"""XGBoost prediction models for traffic, bounce, conversion and sales.

A single :class:`TrafficPredictor` trains one XGBoost regressor per target so
the platform can forecast every headline KPI from the same feature set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from trafficpilot.config import ARTIFACTS_DIR, FEATURE_COLUMNS, RANDOM_STATE, TARGETS


@dataclass
class TrafficPredictor:
    """Multi-target XGBoost forecaster.

    Predicts ``total_traffic``, ``bounce_rate``, ``conversion_rate`` and
    ``sales`` from the site-metric feature columns.
    """

    feature_columns: list[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))
    targets: list[str] = field(default_factory=lambda: list(TARGETS))
    models: dict[str, XGBRegressor] = field(default_factory=dict)
    metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    # Sales is derived from traffic & conversion, so exclude it as a feature.
    def _features_for(self, target: str) -> list[str]:
        return [c for c in self.feature_columns if c != target]

    def fit(self, df: pd.DataFrame, test_size: float = 0.2) -> "TrafficPredictor":
        """Train one regressor per target and record hold-out metrics."""
        for target in self.targets:
            feats = self._features_for(target)
            X = df[feats]
            y = df[target]
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=RANDOM_STATE
            )
            model = XGBRegressor(
                n_estimators=400,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            self.models[target] = model
            self.metrics[target] = {
                "r2": float(r2_score(y_test, preds)),
                "mae": float(mean_absolute_error(y_test, preds)),
            }
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict every target for the given feature rows."""
        if not self.models:
            raise RuntimeError("Model is not trained. Call fit() or load() first.")
        out = {}
        for target, model in self.models.items():
            feats = self._features_for(target)
            out[target] = model.predict(df[feats])
        return pd.DataFrame(out, index=df.index)

    def forecast_next(self, df: pd.DataFrame, horizon: int = 14) -> pd.DataFrame:
        """Naive KPI forecast for ``horizon`` future days.

        Features are projected forward from a short rolling average of the most
        recent history, then fed through the trained models. This is a
        lightweight forecast intended for the dashboard, not a full time-series
        model.
        """
        recent = df.tail(30)
        base = recent[self.feature_columns].mean()
        future = pd.DataFrame([base] * horizon).reset_index(drop=True)
        # add a mild continuation of the recent linear trend
        trend = recent[self.feature_columns].diff().mean().fillna(0)
        for i in range(horizon):
            future.iloc[i] = base + trend * (i + 1)
        preds = self.predict(future)
        preds.insert(0, "day", range(1, horizon + 1))
        return preds

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def save(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path else ARTIFACTS_DIR / "traffic_predictor.joblib"
        joblib.dump(
            {
                "feature_columns": self.feature_columns,
                "targets": self.targets,
                "models": self.models,
                "metrics": self.metrics,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "TrafficPredictor":
        path = Path(path) if path else ARTIFACTS_DIR / "traffic_predictor.joblib"
        blob = joblib.load(path)
        obj = cls(feature_columns=blob["feature_columns"], targets=blob["targets"])
        obj.models = blob["models"]
        obj.metrics = blob["metrics"]
        return obj
