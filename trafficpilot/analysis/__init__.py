"""SEO analysis and AI recommendation engine."""

from trafficpilot.analysis.seo import (
    seo_score_breakdown,
    google_index_status,
    keyword_opportunities,
    competitor_comparison,
)
from trafficpilot.analysis.recommendations import RecommendationEngine

__all__ = [
    "seo_score_breakdown",
    "google_index_status",
    "keyword_opportunities",
    "competitor_comparison",
    "RecommendationEngine",
]
