"""Tests for the real-website audit pipeline.

The HTML parsing, scoring, keyword, geo and indexing helpers are pure functions
that run against a saved fixture — no network required. A single end-to-end test
serves the fixture over real HTTP on localhost to exercise the fetch path.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest

from trafficpilot.audit.audit import (
    audit_site,
    build_recommendations,
    index_status,
    score_onpage,
)
from trafficpilot.audit.geo import assess_geo
from trafficpilot.audit.indexing import (
    build_payload,
    generate_sitemap,
    make_indexnow_key,
    submit_indexnow,
)
from trafficpilot.audit.keywords import extract_keywords
from trafficpilot.audit.onpage import analyze_html

FIXTURE = Path(__file__).parent / "fixtures" / "sample_store.html"
HTML = FIXTURE.read_text(encoding="utf-8")
URL = "https://example-store.test/"


def test_analyze_html_extracts_core_signals():
    op = analyze_html(HTML, URL)
    assert op["title_ok"] is True
    assert op["description_ok"] is True
    assert op["h1_count"] == 1
    assert op["mobile_friendly"] is True
    assert op["has_canonical"] is True
    assert op["has_structured_data"] is True
    assert "Store" in op["schema_types"]
    assert set(op["hreflang"]) == {"en", "bn"}
    assert op["images_missing_alt"] == 1  # the belt image has no alt


def test_score_onpage_bounds_and_grade():
    op = analyze_html(HTML, URL)
    s = score_onpage(op, elapsed=0.2)
    assert 0 <= s["overall"] <= 100
    assert s["grade"] in {"A", "B", "C", "D", "F"}
    assert set(s["components"]) >= {"title", "mobile_friendly", "https", "page_speed"}


def test_index_status_flags_noindex():
    op = analyze_html(HTML, URL)
    op["noindex"] = True
    idx = index_status(op, {"present": True, "blocks_all": False}, {"present": True, "url_count": 5})
    assert idx["indexable"] is False
    assert any("noindex" in w for w in idx["warnings"])


def test_keyword_extraction_finds_theme():
    kw = extract_keywords(HTML)
    terms = {u["term"] for u in kw["unigrams"]}
    assert "leather" in terms
    bigrams = {b["term"] for b in kw["bigrams"]}
    assert any("leather" in b for b in bigrams)


def test_geo_assessment_and_recs():
    op = analyze_html(HTML, URL)
    geo = assess_geo(op, target_country="BD")
    assert 0 <= geo["readiness_score"] <= 100
    assert geo["signals"]["hreflang"] is True
    assert geo["signals"]["local_business_schema"] is True
    assert any(r["category"] == "geo" for r in geo["recommendations"])


def test_recommendations_sorted_by_priority():
    op = analyze_html(HTML, URL)
    s = score_onpage(op, 0.2)
    idx = index_status(op, {"present": True, "blocks_all": False}, {"present": True, "url_count": 2})
    geo = assess_geo(op, "BD")
    recs = build_recommendations(op, s, idx, geo)
    order = {"High": 0, "Medium": 1, "Low": 2}
    prio = [order[r["priority"]] for r in recs]
    assert prio == sorted(prio)


def test_indexnow_helpers():
    key = make_indexnow_key("example.com")
    assert len(key) == 32
    payload = build_payload("example.com", key, ["https://example.com/a"])
    assert payload["host"] == "example.com"
    assert payload["urlList"] == ["https://example.com/a"]
    # dry-run never touches the network
    out = submit_indexnow(["https://example.com/a"], dry_run=True)
    assert out["dry_run"] is True


def test_generate_sitemap_is_valid_xml():
    from xml.dom.minidom import parseString

    xml = generate_sitemap(["https://example.com/", "https://example.com/products"])
    doc = parseString(xml)  # raises if malformed
    assert len(doc.getElementsByTagName("loc")) == 2


def test_audit_bad_url_returns_error():
    res = audit_site("http://127.0.0.1:1/")  # nothing listening
    assert res.ok is False
    assert res.error


def test_audit_end_to_end_over_http():
    """Serve the fixture on localhost and run the full audit through fetch()."""
    robots = "User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:8911/sitemap.xml\n"
    sitemap = ('<?xml version="1.0"?><urlset><url><loc>http://127.0.0.1:8911/</loc></url>'
               '<url><loc>http://127.0.0.1:8911/p</loc></url></urlset>')

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            if self.path.startswith("/robots.txt"):
                self._send(robots, "text/plain")
            elif self.path.startswith("/sitemap.xml"):
                self._send(sitemap, "application/xml")
            else:
                self._send(HTML, "text/html; charset=utf-8")

        def log_message(self, *a):
            pass

    with socketserver.TCPServer(("127.0.0.1", 8911), Handler) as srv:
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            res = audit_site("http://127.0.0.1:8911/", target_country="BD")
        finally:
            srv.shutdown()

    assert res.ok is True
    assert res.seo_score["grade"] in {"A", "B", "C", "D", "F"}
    assert res.index_status["sitemap_url_count"] == 2
    assert res.recommendations
    assert res.keywords["bigrams"]
