"""Central configuration: paths, feature definitions and constants."""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATA_DIR = PROJECT_ROOT / "data_store"

ARTIFACTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
RANDOM_STATE = 42

# --------------------------------------------------------------------------- #
# Daily site-metrics dataset
#
# These are the input signals TrafficPilot tracks for a website. The regression
# models use FEATURE_COLUMNS to predict each entry in TARGETS.
# --------------------------------------------------------------------------- #
FEATURE_COLUMNS = [
    "organic_traffic",       # organic search sessions
    "paid_traffic",          # paid / ads sessions
    "referral_traffic",      # referral sessions
    "direct_traffic",        # direct sessions
    "seo_score",             # 0-100 on-page + technical SEO health
    "page_speed",            # median load time in seconds (lower is better)
    "backlinks",             # number of referring backlinks
    "domain_authority",      # 0-100 domain authority
    "keyword_rank_avg",      # avg SERP position of tracked keywords (lower better)
    "content_freshness_days",  # days since content was last refreshed
    "mobile_friendly",       # 1 if the site passes mobile-friendly checks
    "indexed_pages",         # number of pages indexed by Google
]

# Regression targets predicted with XGBoost.
TARGETS = ["total_traffic", "bounce_rate", "conversion_rate", "sales"]

# --------------------------------------------------------------------------- #
# Visitor-level dataset (used by K-Means segmentation)
# --------------------------------------------------------------------------- #
VISITOR_FEATURES = [
    "sessions",              # sessions in the period
    "avg_session_duration",  # seconds
    "pages_per_session",
    "recency_days",          # days since last visit
    "total_spend",           # lifetime spend
    "is_returning",          # 1 if returning visitor
]

DEFAULT_N_SEGMENTS = 4

# --------------------------------------------------------------------------- #
# Business assumptions used by SEO / recommendation heuristics
# --------------------------------------------------------------------------- #
GOOD_PAGE_SPEED = 2.5          # seconds — target load time
GOOD_SEO_SCORE = 75            # target SEO score
GOOD_BOUNCE_RATE = 45.0        # % — anything higher is a warning
TARGET_TOP_RANK = 10          # first-page SERP position
