"""AI recommendation engine.

Combines the Random-Forest importance ranking, the current site metrics, the
SEO breakdown and keyword opportunities into a prioritised, human-readable set
of growth recommendations: which pages to improve, what content to write and
which keywords to target.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trafficpilot.analysis.seo import (
    keyword_opportunities,
    seo_score_breakdown,
)
from trafficpilot.config import (
    GOOD_BOUNCE_RATE,
    GOOD_PAGE_SPEED,
    GOOD_SEO_SCORE,
    TARGET_TOP_RANK,
)


@dataclass
class Recommendation:
    title: str
    detail: str
    category: str          # seo | speed | content | keywords | conversion
    priority: str          # High | Medium | Low
    expected_impact: str   # short human phrase

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "detail": self.detail,
            "category": self.category,
            "priority": self.priority,
            "expected_impact": self.expected_impact,
        }


_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


class RecommendationEngine:
    """Generate prioritised recommendations from metrics + model signals."""

    def __init__(self, importance: pd.DataFrame | None = None):
        # importance: DataFrame with columns [feature, importance]
        self._importance = importance

    def _importance_of(self, feature: str) -> float:
        if self._importance is None:
            return 0.5
        row = self._importance.loc[self._importance["feature"] == feature, "importance"]
        return float(row.iloc[0]) if len(row) else 0.0

    def _priority_from_impact(self, gap: float, importance: float) -> str:
        score = gap * (0.5 + importance)
        if score >= 0.6:
            return "High"
        if score >= 0.25:
            return "Medium"
        return "Low"

    def generate(
        self,
        metrics: dict,
        keywords: pd.DataFrame | None = None,
    ) -> list[Recommendation]:
        recs: list[Recommendation] = []

        # --- page speed --------------------------------------------------- #
        speed = metrics.get("page_speed", GOOD_PAGE_SPEED)
        if speed > GOOD_PAGE_SPEED:
            gap = min((speed - GOOD_PAGE_SPEED) / GOOD_PAGE_SPEED, 1.0)
            recs.append(
                Recommendation(
                    title="Improve page load speed",
                    detail=(
                        f"Median load time is {speed:.1f}s; aim for under "
                        f"{GOOD_PAGE_SPEED:.1f}s. Compress images, enable caching "
                        "and defer non-critical JavaScript."
                    ),
                    category="speed",
                    priority=self._priority_from_impact(gap, self._importance_of("page_speed")),
                    expected_impact="Lower bounce, better crawl budget & rankings",
                )
            )

        # --- SEO score ---------------------------------------------------- #
        seo = metrics.get("seo_score", GOOD_SEO_SCORE)
        if seo < GOOD_SEO_SCORE:
            gap = min((GOOD_SEO_SCORE - seo) / GOOD_SEO_SCORE, 1.0)
            breakdown = seo_score_breakdown(metrics)
            weakest = min(breakdown["components"], key=breakdown["components"].get)
            recs.append(
                Recommendation(
                    title="Raise on-page & technical SEO",
                    detail=(
                        f"SEO score is {seo:.0f}/100 (grade {breakdown['grade']}). "
                        f"Weakest component: '{weakest.replace('_', ' ')}'. Fix titles, "
                        "meta descriptions, headings and internal links first."
                    ),
                    category="seo",
                    priority=self._priority_from_impact(gap, self._importance_of("seo_score")),
                    expected_impact="More organic traffic",
                )
            )

        # --- content freshness ------------------------------------------- #
        fresh = metrics.get("content_freshness_days", 0)
        if fresh > 90:
            gap = min(fresh / 300, 1.0)
            recs.append(
                Recommendation(
                    title="Refresh stale content",
                    detail=(
                        f"Top content is ~{int(fresh)} days old. Update your highest-"
                        "traffic pages with new data, examples and internal links, and "
                        "publish one new cornerstone article this month."
                    ),
                    category="content",
                    priority=self._priority_from_impact(gap, self._importance_of("content_freshness_days")),
                    expected_impact="Regained rankings & engagement",
                )
            )

        # --- bounce rate -------------------------------------------------- #
        bounce = metrics.get("bounce_rate")
        if bounce is not None and bounce > GOOD_BOUNCE_RATE:
            gap = min((bounce - GOOD_BOUNCE_RATE) / 50, 1.0)
            recs.append(
                Recommendation(
                    title="Reduce bounce rate on landing pages",
                    detail=(
                        f"Bounce rate is {bounce:.0f}%. Match landing-page content to ad "
                        "and search intent, add a clear above-the-fold call to action, and "
                        "improve readability."
                    ),
                    category="conversion",
                    priority="High" if bounce > 65 else "Medium",
                    expected_impact="Higher conversion rate",
                )
            )

        # --- mobile ------------------------------------------------------- #
        if not metrics.get("mobile_friendly", 1):
            recs.append(
                Recommendation(
                    title="Fix mobile usability",
                    detail=(
                        "The site failed mobile-friendly checks. Use a responsive layout, "
                        "legible font sizes and tap-friendly buttons — Google indexes "
                        "mobile-first."
                    ),
                    category="seo",
                    priority="High",
                    expected_impact="Avoids mobile ranking penalties",
                )
            )

        # --- keyword targeting ------------------------------------------- #
        if keywords is not None and len(keywords):
            opps = keyword_opportunities(keywords, top_n=3)
            for _, row in opps.iterrows():
                recs.append(
                    Recommendation(
                        title=f"Target keyword: '{row['keyword']}'",
                        detail=(
                            f"Volume {int(row['search_volume']):,}/mo, difficulty "
                            f"{int(row['difficulty'])}/100, currently ranked "
                            f"#{int(row['current_rank'])}. Build a focused page/article to "
                            f"push it into the top {TARGET_TOP_RANK}."
                        ),
                        category="keywords",
                        priority=str(row["priority"]),
                        expected_impact="New organic traffic",
                    )
                )

        recs.sort(key=lambda r: _PRIORITY_ORDER.get(r.priority, 3))
        return recs

    def generate_dicts(
        self, metrics: dict, keywords: pd.DataFrame | None = None
    ) -> list[dict]:
        return [r.as_dict() for r in self.generate(metrics, keywords)]
