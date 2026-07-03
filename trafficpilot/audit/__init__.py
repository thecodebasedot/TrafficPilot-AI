"""Real-website audit: crawl a live URL and run SEO / technical analysis.

Unlike :mod:`trafficpilot.data` (which synthesises data for the ML demo), this
package fetches a **real** website and measures its actual on-page and technical
SEO signals, extracts keywords, assesses geo/region readiness and produces
prioritised recommendations.

Entry point: :func:`trafficpilot.audit.audit.audit_site`.
"""

from trafficpilot.audit.audit import audit_site, SiteAudit

__all__ = ["audit_site", "SiteAudit"]
