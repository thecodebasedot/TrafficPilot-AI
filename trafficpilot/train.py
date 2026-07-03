"""Train every TrafficPilot model and persist the artifacts.

Run with::

    python -m trafficpilot.train

This generates the synthetic datasets, trains the XGBoost predictors, the
Random-Forest importance analyzer and the K-Means segmenter, saves them to the
``artifacts/`` directory and prints a short report.
"""

from __future__ import annotations

import json

from trafficpilot.config import ARTIFACTS_DIR, DATA_DIR
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


def main() -> dict:
    print("TrafficPilot AI — training pipeline")
    print("=" * 50)

    # 1. data ------------------------------------------------------------- #
    print("• Generating synthetic datasets ...")
    site = generate_site_metrics()
    visitors = generate_visitors()
    keywords = generate_keywords()
    competitors = generate_competitors()

    site.to_csv(DATA_DIR / "site_metrics.csv", index=False)
    visitors.to_csv(DATA_DIR / "visitors.csv", index=False)
    keywords.to_csv(DATA_DIR / "keywords.csv", index=False)
    competitors.to_csv(DATA_DIR / "competitors.csv", index=False)

    # 2. XGBoost predictors ---------------------------------------------- #
    print("• Training XGBoost predictors (traffic, bounce, conversion, sales) ...")
    predictor = TrafficPredictor().fit(site)
    predictor.save()
    for target, m in predictor.metrics.items():
        print(f"    {target:16s}  R2={m['r2']:.3f}  MAE={m['mae']:.2f}")

    # 3. Random-Forest importance ---------------------------------------- #
    print("• Training Random-Forest importance analyzer (target=sales) ...")
    analyzer = FeatureImportanceAnalyzer(target="sales").fit(site)
    analyzer.save()
    print(f"    R2={analyzer.r2:.3f}")
    for d in analyzer.top_drivers(5):
        print(f"    {d['feature']:22s}  {d['importance']:.3f}")

    # 4. K-Means segmentation -------------------------------------------- #
    print("• Training K-Means visitor segmenter ...")
    segmenter = VisitorSegmenter().fit(visitors)
    segmenter.save()
    sil = segmenter.silhouette
    print(f"    silhouette={sil:.3f}" if sil is not None else "    silhouette=n/a")
    for _, row in segmenter.profile(visitors).iterrows():
        print(f"    {row['label']:20s}  {int(row['visitors'])} visitors ({row['share_pct']}%)")

    # 5. report ----------------------------------------------------------- #
    report = {
        "predictor_metrics": predictor.metrics,
        "importance_r2": analyzer.r2,
        "top_drivers": analyzer.top_drivers(5),
        "segmenter_silhouette": segmenter.silhouette,
    }
    (ARTIFACTS_DIR / "training_report.json").write_text(json.dumps(report, indent=2))

    print("=" * 50)
    print(f"✔ Artifacts saved to {ARTIFACTS_DIR}")
    print(f"✔ Datasets saved to  {DATA_DIR}")
    return report


if __name__ == "__main__":
    main()
