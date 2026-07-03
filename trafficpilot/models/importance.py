"""Random-Forest feature-importance analysis.

Answers the question "which factors influence our growth the most?" by fitting
a Random Forest against a chosen target (sales by default) and ranking the
input signals by importance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

from trafficpilot.config import ARTIFACTS_DIR, FEATURE_COLUMNS, RANDOM_STATE


@dataclass
class FeatureImportanceAnalyzer:
    """Rank the drivers of a target metric using a Random Forest."""

    target: str = "sales"
    feature_columns: list[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))
    model: RandomForestRegressor | None = None
    r2: float | None = None

    def fit(self, df: pd.DataFrame, test_size: float = 0.2) -> "FeatureImportanceAnalyzer":
        feats = [c for c in self.feature_columns if c != self.target]
        self.feature_columns = feats
        X, y = df[feats], df[self.target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_STATE
        )
        self.model = RandomForestRegressor(
            n_estimators=300,
            max_depth=None,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        self.model.fit(X_train, y_train)
        self.r2 = float(r2_score(y_test, self.model.predict(X_test)))
        return self

    def importances(self, normalize: bool = True) -> pd.DataFrame:
        """Return features ranked by importance (most influential first)."""
        if self.model is None:
            raise RuntimeError("Analyzer is not trained. Call fit() first.")
        imp = self.model.feature_importances_
        if normalize and imp.sum() > 0:
            imp = imp / imp.sum()
        df = pd.DataFrame(
            {"feature": self.feature_columns, "importance": imp}
        ).sort_values("importance", ascending=False, ignore_index=True)
        return df

    def top_drivers(self, n: int = 5) -> list[dict]:
        """Convenience: top-n drivers as a list of dicts for the API/UI."""
        return self.importances().head(n).to_dict(orient="records")

    # ------------------------------------------------------------------ #
    def save(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path else ARTIFACTS_DIR / "importance.joblib"
        joblib.dump(
            {
                "target": self.target,
                "feature_columns": self.feature_columns,
                "model": self.model,
                "r2": self.r2,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "FeatureImportanceAnalyzer":
        path = Path(path) if path else ARTIFACTS_DIR / "importance.joblib"
        blob = joblib.load(path)
        obj = cls(target=blob["target"], feature_columns=blob["feature_columns"])
        obj.model = blob["model"]
        obj.r2 = blob["r2"]
        return obj
