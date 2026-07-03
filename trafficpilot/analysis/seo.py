"""SEO analytics helpers.

These functions turn raw site metrics into the SEO-focused views the platform
exposes: an SEO score breakdown, a Google index-status check, keyword
opportunity scoring, and a competitor comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trafficpilot.config import (
    GOOD_PAGE_SPEED,
    GOOD_SEO_SCORE,
    TARGET_TOP_RANK,
)


def seo_score_breakdown(metrics: dict) -> dict:
    """Break the headline SEO score into weighted component sub-scores.

    ``metrics`` is a dict of the latest site metrics. Returns component scores
    (0-100) plus a weighted overall score and a letter grade.
    """
    speed = metrics.get("page_speed", GOOD_PAGE_SPEED)
    speed_score = float(np.clip(100 - (speed - GOOD_PAGE_SPEED) * 22, 0, 100))

    authority = float(np.clip(metrics.get("domain_authority", 30), 0, 100))

    rank = metrics.get("keyword_rank_avg", 25)
    rank_score = float(np.clip(100 - (rank - 1) * 1.6, 0, 100))

    freshness = metrics.get("content_freshness_days", 60)
    freshness_score = float(np.clip(100 - freshness * 0.6, 0, 100))

    mobile_score = 100.0 if metrics.get("mobile_friendly", 1) else 40.0

    backlinks = metrics.get("backlinks", 500)
    backlink_score = float(np.clip(np.log10(max(backlinks, 1)) * 25, 0, 100))

    components = {
        "page_speed": round(speed_score, 1),
        "domain_authority": round(authority, 1),
        "keyword_ranking": round(rank_score, 1),
        "content_freshness": round(freshness_score, 1),
        "mobile_friendly": round(mobile_score, 1),
        "backlinks": round(backlink_score, 1),
    }
    weights = {
        "page_speed": 0.20,
        "domain_authority": 0.20,
        "keyword_ranking": 0.20,
        "content_freshness": 0.15,
        "mobile_friendly": 0.10,
        "backlinks": 0.15,
    }
    overall = round(sum(components[k] * weights[k] for k in components), 1)
    return {
        "components": components,
        "weights": weights,
        "overall": overall,
        "grade": _grade(overall),
    }


def _grade(score: float) -> str:
    for threshold, grade in [(90, "A"), (80, "B"), (70, "C"), (55, "D")]:
        if score >= threshold:
            return grade
    return "F"


def google_index_status(metrics: dict) -> dict:
    """Heuristic Google index-health check for the site.

    Estimates the share of pages indexed and flags whether the site looks
    healthily indexed based on indexed-page count, crawl-friendliness signals
    (speed, mobile) and SEO score.
    """
    indexed = int(metrics.get("indexed_pages", 0))
    # assume the site publishes ~15% more pages than are indexed on a healthy site
    estimated_total = max(indexed, int(indexed * 1.15) + 1)
    coverage = round(indexed / estimated_total * 100, 1) if estimated_total else 0.0

    speed_ok = metrics.get("page_speed", 3) <= GOOD_PAGE_SPEED + 1.5
    mobile_ok = bool(metrics.get("mobile_friendly", 1))
    seo_ok = metrics.get("seo_score", 0) >= GOOD_SEO_SCORE - 15

    healthy = indexed >= 100 and speed_ok and mobile_ok and seo_ok
    warnings = []
    if indexed < 100:
        warnings.append("Very few pages indexed — submit an XML sitemap to Google Search Console.")
    if not speed_ok:
        warnings.append("Slow pages can reduce crawl budget and delay indexing.")
    if not mobile_ok:
        warnings.append("Site is not mobile-friendly — mobile-first indexing may suffer.")
    if not seo_ok:
        warnings.append("Low SEO score — thin or duplicate content may be excluded from the index.")

    return {
        "indexed_pages": indexed,
        "estimated_total_pages": estimated_total,
        "coverage_pct": coverage,
        "status": "healthy" if healthy else "needs attention",
        "warnings": warnings,
    }


def keyword_opportunities(keywords: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Score keywords by opportunity and return the best targets.

    Opportunity favours high search volume and low difficulty, and rewards
    keywords sitting just off page one (ranks 4-20) where a small push yields
    outsized traffic gains.
    """
    df = keywords.copy()
    volume_norm = df["search_volume"] / df["search_volume"].max()
    difficulty_norm = df["difficulty"] / 100.0

    # "striking distance" bonus for near-first-page ranks
    def _proximity(rank: int) -> float:
        if rank <= TARGET_TOP_RANK:
            return 0.3            # already ranking well, less upside
        if rank <= 20:
            return 1.0            # sweet spot
        return 0.5

    proximity = df["current_rank"].apply(_proximity)
    df["opportunity"] = (
        (0.5 * volume_norm + 0.5 * proximity) * (1 - 0.6 * difficulty_norm)
    ).round(3)
    df["priority"] = pd.cut(
        df["opportunity"],
        bins=[-1, 0.25, 0.45, 1.0],
        labels=["Low", "Medium", "High"],
    )
    return df.sort_values("opportunity", ascending=False).head(top_n).reset_index(drop=True)


def competitor_comparison(competitors: pd.DataFrame, you: str = "Your Site") -> dict:
    """Compare your site against competitors and surface gaps."""
    df = competitors.copy()
    metrics = ["monthly_traffic", "domain_authority", "backlinks", "avg_keyword_rank", "page_speed"]
    # lower is better for rank & page_speed
    lower_is_better = {"avg_keyword_rank", "page_speed"}

    ranks = {}
    for m in metrics:
        ascending = m in lower_is_better
        df[f"{m}_rank"] = df[m].rank(ascending=ascending, method="min").astype(int)
        ranks[m] = int(df.loc[df["site"] == you, f"{m}_rank"].iloc[0])

    gaps = []
    your_row = df[df["site"] == you].iloc[0]
    for m in metrics:
        best_site = df.loc[df[m].idxmin() if m in lower_is_better else df[m].idxmax(), "site"]
        if best_site != you:
            best_val = df.loc[df["site"] == best_site, m].iloc[0]
            gaps.append(
                {
                    "metric": m,
                    "you": float(your_row[m]),
                    "leader": best_site,
                    "leader_value": float(best_val),
                }
            )
    return {
        "your_ranks": ranks,
        "n_sites": len(df),
        "gaps": gaps,
        "table": df[["site"] + metrics].to_dict(orient="records"),
    }
