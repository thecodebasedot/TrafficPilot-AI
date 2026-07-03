"""Synthetic-but-realistic data generation.

Because TrafficPilot ships without a live analytics connection, we synthesise
datasets whose signals follow believable business relationships so that the
XGBoost / Random-Forest / K-Means models learn something meaningful:

* Better SEO score, more backlinks and higher domain authority  -> more traffic
* Faster pages and fresher content                              -> lower bounce
* Lower bounce + stronger SEO                                   -> more conversions
* Sales follow from traffic x conversion x average order value

All relationships are deliberately noisy so the models are not trivial.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trafficpilot.config import RANDOM_STATE


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(RANDOM_STATE if seed is None else seed)


def generate_site_metrics(n_days: int = 720, seed: int | None = None) -> pd.DataFrame:
    """Generate a daily site-metrics dataset.

    Returns one row per day with the feature signals plus the derived targets
    (total_traffic, bounce_rate, conversion_rate, sales).
    """
    rng = _rng(seed)
    n = n_days

    # --- underlying site "quality" signals -------------------------------- #
    seo_score = np.clip(rng.normal(62, 14, n), 5, 100)
    page_speed = np.clip(rng.normal(3.4, 1.1, n), 0.6, 9.0)          # seconds
    backlinks = np.clip(rng.gamma(3.0, 400, n), 10, None).astype(int)
    domain_authority = np.clip(rng.normal(38, 15, n), 1, 95)
    keyword_rank_avg = np.clip(rng.normal(24, 12, n), 1, 100)         # lower better
    content_freshness_days = np.clip(rng.exponential(45, n), 0, 400).astype(int)
    mobile_friendly = (rng.random(n) < 0.8).astype(int)
    indexed_pages = np.clip(rng.normal(1200, 600, n), 20, None).astype(int)

    # weekly seasonality (weekends dip a little)
    day_idx = np.arange(n)
    seasonality = 1 + 0.12 * np.sin(2 * np.pi * day_idx / 7)
    trend = 1 + 0.0004 * day_idx  # mild organic growth over time

    # --- traffic channels ------------------------------------------------- #
    # organic traffic driven by SEO health, backlinks, DA and good ranking
    organic_base = (
        18 * seo_score
        + 0.9 * backlinks
        + 22 * domain_authority
        + 40 * (50 - keyword_rank_avg)
    )
    organic_traffic = np.clip(
        organic_base * seasonality * trend * rng.normal(1.0, 0.10, n), 30, None
    ).astype(int)

    paid_traffic = np.clip(
        rng.gamma(2.0, 350, n) * seasonality * rng.normal(1.0, 0.15, n), 0, None
    ).astype(int)
    referral_traffic = np.clip(
        (0.15 * backlinks + rng.normal(300, 150, n)) * seasonality, 0, None
    ).astype(int)
    direct_traffic = np.clip(
        (6 * domain_authority + rng.normal(400, 180, n)) * seasonality, 0, None
    ).astype(int)

    total_traffic = organic_traffic + paid_traffic + referral_traffic + direct_traffic

    # --- bounce rate (%) -------------------------------------------------- #
    # slow pages and stale content raise bounce; good SEO lowers it
    bounce_rate = (
        70
        + 3.5 * (page_speed - 2.5)
        + 0.03 * content_freshness_days
        - 0.18 * seo_score
        - 4.0 * mobile_friendly
        + rng.normal(0, 3.0, n)
    )
    bounce_rate = np.clip(bounce_rate, 15, 92)

    # --- conversion rate (%) --------------------------------------------- #
    # lower bounce and stronger SEO convert better; slow pages hurt
    conversion_rate = (
        4.5
        - 0.045 * bounce_rate
        + 0.02 * seo_score
        - 0.25 * (page_speed - 2.5)
        + 0.4 * mobile_friendly
        + rng.normal(0, 0.35, n)
    )
    conversion_rate = np.clip(conversion_rate, 0.1, 12.0)

    # --- sales ------------------------------------------------------------ #
    avg_order_value = np.clip(rng.normal(55, 12, n), 15, None)
    conversions = total_traffic * (conversion_rate / 100.0)
    sales = np.clip(conversions * avg_order_value * rng.normal(1.0, 0.08, n), 0, None)

    dates = pd.date_range(end=pd.Timestamp("2025-01-01"), periods=n, freq="D")

    df = pd.DataFrame(
        {
            "date": dates,
            "organic_traffic": organic_traffic,
            "paid_traffic": paid_traffic,
            "referral_traffic": referral_traffic,
            "direct_traffic": direct_traffic,
            "seo_score": seo_score.round(1),
            "page_speed": page_speed.round(2),
            "backlinks": backlinks,
            "domain_authority": domain_authority.round(1),
            "keyword_rank_avg": keyword_rank_avg.round(1),
            "content_freshness_days": content_freshness_days,
            "mobile_friendly": mobile_friendly,
            "indexed_pages": indexed_pages,
            "total_traffic": total_traffic,
            "bounce_rate": bounce_rate.round(2),
            "conversion_rate": conversion_rate.round(3),
            "sales": sales.round(2),
        }
    )
    return df


def generate_visitors(n_visitors: int = 3000, seed: int | None = None) -> pd.DataFrame:
    """Generate a visitor-level dataset used for K-Means segmentation.

    Three latent groups are mixed together (loyal high-value, casual browsers,
    one-off bargain hunters) so clustering has real structure to recover.
    """
    rng = _rng(seed)

    def _group(size, sess, dur, ppv, rec, spend, ret_p):
        return pd.DataFrame(
            {
                "sessions": np.clip(rng.normal(*sess, size), 1, None).astype(int),
                "avg_session_duration": np.clip(rng.normal(*dur, size), 5, None).round(1),
                "pages_per_session": np.clip(rng.normal(*ppv, size), 1, None).round(2),
                "recency_days": np.clip(rng.exponential(rec, size), 0, 365).astype(int),
                "total_spend": np.clip(rng.normal(*spend, size), 0, None).round(2),
                "is_returning": (rng.random(size) < ret_p).astype(int),
            }
        )

    n1 = int(n_visitors * 0.30)   # loyal high-value
    n2 = int(n_visitors * 0.45)   # casual browsers
    n3 = n_visitors - n1 - n2     # one-off bargain hunters

    loyal = _group(n1, (14, 5), (320, 90), (7.5, 2.0), 8, (480, 160), 0.9)
    casual = _group(n2, (4, 2), (150, 60), (3.2, 1.2), 30, (90, 60), 0.4)
    oneoff = _group(n3, (1.4, 0.8), (55, 25), (1.6, 0.7), 120, (25, 20), 0.05)

    df = pd.concat([loyal, casual, oneoff], ignore_index=True)
    return df.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)


def generate_keywords(n_keywords: int = 40, seed: int | None = None) -> pd.DataFrame:
    """Generate a tracked-keyword table for keyword-opportunity analysis."""
    rng = _rng(seed)
    topics = [
        "seo", "analytics", "traffic", "conversion", "growth", "marketing",
        "keywords", "backlinks", "content", "ranking", "ecommerce", "leads",
        "automation", "dashboard", "insights", "audience", "campaign", "funnel",
    ]
    words = rng.choice(topics, size=(n_keywords, 2))
    keywords = [f"{a} {b}" for a, b in words]

    df = pd.DataFrame(
        {
            "keyword": keywords,
            "search_volume": rng.integers(80, 40000, n_keywords),
            "current_rank": rng.integers(1, 90, n_keywords),
            "difficulty": rng.integers(5, 95, n_keywords),          # 0-100
            "cpc": (rng.random(n_keywords) * 6 + 0.2).round(2),      # $
        }
    )
    return df.drop_duplicates(subset="keyword").reset_index(drop=True)


def generate_competitors(seed: int | None = None) -> pd.DataFrame:
    """Generate a small competitor-benchmark table."""
    rng = _rng(seed)
    names = ["Your Site", "Competitor A", "Competitor B", "Competitor C"]
    df = pd.DataFrame(
        {
            "site": names,
            "monthly_traffic": [rng.integers(40000, 90000)] +
            list(rng.integers(30000, 200000, len(names) - 1)),
            "domain_authority": np.clip(rng.normal(45, 18, len(names)), 5, 95).round(0),
            "backlinks": rng.integers(500, 90000, len(names)),
            "avg_keyword_rank": np.clip(rng.normal(20, 10, len(names)), 1, 80).round(1),
            "page_speed": np.clip(rng.normal(3.0, 1.0, len(names)), 0.8, 8).round(2),
        }
    )
    return df


if __name__ == "__main__":  # pragma: no cover
    print(generate_site_metrics().head())
    print(generate_visitors().head())
    print(generate_keywords().head())
    print(generate_competitors())
