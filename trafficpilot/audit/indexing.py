"""Legitimate (white-hat) indexing helpers.

You cannot force Google to rank a page, but you *can* legitimately tell search
engines a URL exists so they crawl/index it faster:

* **IndexNow** — an open protocol (Bing, Yandex, Naver, Seznam) that instantly
  notifies engines of new/updated URLs. This module builds the key file and the
  submission payload, and can POST it.
* **Sitemap** — generate a valid ``sitemap.xml`` from a URL list to submit in
  Google Search Console.

Google itself does not accept anonymous "ping" submissions any more — for Google
you verify the site in Search Console and submit the sitemap there (and may use
the Indexing API for job-posting / livestream pages). These helpers prepare
exactly what those workflows need.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import requests

from trafficpilot.audit.fetch import USER_AGENT

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
_CA = os.environ.get("REQUESTS_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
_VERIFY = _CA if os.path.exists(_CA) else True


def make_indexnow_key(seed: str = "trafficpilot") -> str:
    """Derive a deterministic 32-char hex IndexNow key from a seed.

    (Deterministic so tests are stable; in production any 8–128 char hex key that
    you host at ``/<key>.txt`` on your domain is valid.)
    """
    import hashlib

    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def key_file(key: str) -> tuple[str, str]:
    """Return (filename, contents) for the key file you host at your domain root."""
    return f"{key}.txt", key


def build_payload(host: str, key: str, urls: list[str]) -> dict:
    """Build the IndexNow JSON submission payload."""
    return {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": list(urls),
    }


def submit_indexnow(urls: list[str], key: str | None = None, dry_run: bool = False) -> dict:
    """Submit URLs to IndexNow. Set ``dry_run=True`` to only build the payload."""
    if not urls:
        return {"submitted": 0, "status": "no urls"}
    host = urlparse(urls[0] if "://" in urls[0] else "https://" + urls[0]).netloc
    key = key or make_indexnow_key(host)
    payload = build_payload(host, key, urls)
    if dry_run:
        return {"dry_run": True, "endpoint": INDEXNOW_ENDPOINT, "payload": payload}
    try:
        resp = requests.post(
            INDEXNOW_ENDPOINT, json=payload,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            timeout=20, verify=_VERIFY,
        )
        return {"submitted": len(urls), "http_status": resp.status_code, "ok": resp.ok}
    except requests.RequestException as exc:
        return {"submitted": 0, "error": f"{type(exc).__name__}: {exc}"}


def generate_sitemap(urls: list[str]) -> str:
    """Generate a valid ``sitemap.xml`` string from a list of URLs."""
    items = "".join(f"  <url><loc>{escape(u)}</loc></url>\n" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}"
        "</urlset>\n"
    )
