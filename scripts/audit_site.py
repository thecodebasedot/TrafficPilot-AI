"""Audit a real website from the command line.

Usage::

    python scripts/audit_site.py https://your-website.com --country BD

Crawls the URL and prints a full SEO / technical / keyword / geo report with
prioritised recommendations. Requires outbound internet access.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trafficpilot.audit import audit_site


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit a real website with TrafficPilot AI")
    ap.add_argument("url", help="website URL, e.g. https://example.com")
    ap.add_argument("--country", help="target country code for geo targeting (e.g. BD, US)")
    args = ap.parse_args()

    print(f"Crawling {args.url} …\n")
    a = audit_site(args.url, target_country=args.country)

    if not a.ok:
        print(f"❌ Could not analyze the site: {a.error}")
        sys.exit(1)

    s, op, ix, g = a.seo_score, a.onpage, a.index_status, a.geo
    print("=" * 60)
    print(f"  {a.url}")
    print("=" * 60)
    print(f"SEO score        : {s['overall']}/100  (grade {s['grade']})")
    print(f"Response time    : {a.fetch_info['response_time_s']}s")
    print(f"Index status     : {ix['status']}  (sitemap URLs: {ix['sitemap_url_count']})")
    print(f"Geo readiness    : {g['readiness_score']}%  (target: {g['target_country'] or 'n/a'})")

    print("\nOn-page checks")
    print("-" * 60)
    checks = [
        ("Title (30-60 chars)", op["title_ok"]),
        ("Meta description", op["description_ok"]),
        ("Single H1", op["h1_count"] == 1),
        ("Mobile friendly", op["mobile_friendly"]),
        ("HTTPS", op["https"]),
        ("Canonical tag", op["has_canonical"]),
        ("Structured data", op["has_structured_data"]),
        ("hreflang", op["has_hreflang"]),
    ]
    for name, ok in checks:
        print(f"  [{'✓' if ok else '✗'}] {name}")

    print(f"\nKeywords this page targets ({op['word_count']} words)")
    print("-" * 60)
    print("  " + ", ".join(b["term"] for b in a.keywords["bigrams"][:8]))

    print(f"\nRecommendations ({len(a.recommendations)})")
    print("-" * 60)
    for i, r in enumerate(a.recommendations, 1):
        print(f"  {i}. [{r['priority']}] {r['title']}")
        print(f"     {r['detail']}")

    print("\nNotes")
    print("-" * 60)
    for n in a.notes:
        print(f"  • {n}")


if __name__ == "__main__":
    main()
