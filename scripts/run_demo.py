"""End-to-end demo of the TrafficPilot AI analytics pipeline (no web server).

Run with::

    python scripts/run_demo.py

It trains (or loads) the models and prints a text report covering every core
feature: KPIs, SEO analysis, index status, keyword opportunities, visitor
segments, growth drivers and AI recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# allow running as `python scripts/run_demo.py` from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trafficpilot.service import TrafficPilotService


def _hr(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def main() -> None:
    print("=" * 60)
    print("TrafficPilot AI — Growth Analytics Demo")
    print("=" * 60)

    svc = TrafficPilotService()

    _hr("Headline KPIs")
    k = svc.kpis()
    print(f"Live visitors     : {k['live_visitors']}")
    print(f"Total traffic     : {k['total_traffic']['value']:,} ({k['total_traffic']['delta']:+}% WoW)")
    print(f"Conversion rate   : {k['conversion_rate']['value']}% ({k['conversion_rate']['delta']:+}% WoW)")
    print(f"Bounce rate       : {k['bounce_rate']['value']}%")
    print(f"Page speed        : {k['page_speed']['value']}s")

    _hr("SEO Score")
    seo = svc.seo()
    b = seo["breakdown"]
    print(f"Overall: {b['overall']}/100 (grade {b['grade']})")
    for name, val in b["components"].items():
        print(f"  {name:20s} {val}")
    idx = seo["index_status"]
    print(f"Google index: {idx['status']} — {idx['indexed_pages']:,} pages ({idx['coverage_pct']}% coverage)")

    _hr("Top Keyword Opportunities")
    for row in svc.keyword_table(5):
        print(f"  {row['keyword']:24s} vol={row['search_volume']:>6,}  rank #{row['current_rank']:<3} [{row['priority']}]")

    _hr("Visitor Segments (K-Means)")
    for s in svc.segments():
        print(f"  {s['label']:20s} {int(s['visitors']):>4} visitors ({s['share_pct']}%)  spend=${s['total_spend']:.0f}")

    _hr("Top Growth Drivers (Random Forest)")
    for d in svc.drivers(5):
        print(f"  {d['feature']:22s} {d['importance']*100:.0f}%")

    _hr("14-Day Sales Forecast")
    fc = svc.sales_forecast()
    print(f"  next day  : ${fc['forecast_sales'][0]:,.0f}")
    print(f"  day +7    : ${fc['forecast_sales'][6]:,.0f}")
    print(f"  day +14   : ${fc['forecast_sales'][-1]:,.0f}")

    _hr("AI Recommendations")
    for i, r in enumerate(svc.recommendations(), 1):
        print(f"  {i}. [{r['priority']}] {r['title']}")
        print(f"     {r['detail']}")
        print(f"     -> {r['expected_impact']}")

    print("\n" + "=" * 60)
    print("Done. Launch the dashboard with:  python -m trafficpilot.web.app")
    print("=" * 60)


if __name__ == "__main__":
    main()
