"""HTTP fetching for the real-website audit.

A thin wrapper around ``requests`` that measures response time, follows
redirects, respects the proxy CA bundle when present, and safely fetches the
companion ``robots.txt`` and ``sitemap.xml`` files.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "TrafficPilotBot/0.1 (+https://github.com/thecodebasedot/TrafficPilot-AI)"
DEFAULT_TIMEOUT = 20

# Honour the sandbox / corporate proxy CA bundle if one is configured.
_CA = os.environ.get("REQUESTS_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
_VERIFY = _CA if os.path.exists(_CA) else True


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    ok: bool
    elapsed: float                       # seconds (a rough page-speed proxy)
    html: str = ""
    headers: dict = field(default_factory=dict)
    error: str | None = None


def normalize_url(url: str) -> str:
    """Add a scheme if missing so bare domains ('example.com') still work."""
    url = url.strip()
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch a single URL, returning a :class:`FetchResult` (never raises)."""
    url = normalize_url(url)
    try:
        t0 = time.time()
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
            timeout=timeout,
            allow_redirects=True,
            verify=_VERIFY,
        )
        elapsed = time.time() - t0
        ctype = resp.headers.get("Content-Type", "")
        # requests defaults to ISO-8859-1 when the header omits a charset, which
        # mangles the many UTF-8 pages that declare their charset only in a
        # <meta> tag. Fall back to content-sniffed encoding in that case.
        if "charset" not in ctype.lower():
            resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text if "html" in ctype or not ctype else ""
        return FetchResult(
            url=url,
            final_url=resp.url,
            status=resp.status_code,
            ok=resp.ok,
            elapsed=round(elapsed, 3),
            html=html,
            headers=dict(resp.headers),
        )
    except requests.RequestException as exc:
        return FetchResult(
            url=url, final_url=url, status=0, ok=False, elapsed=0.0,
            error=f"{type(exc).__name__}: {exc}",
        )


def fetch_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Fetch a plain-text resource (robots.txt, sitemap.xml); None on failure."""
    try:
        resp = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout, verify=_VERIFY
        )
        if resp.ok:
            return resp.text
    except requests.RequestException:
        pass
    return None


def base_of(url: str) -> str:
    """Return the scheme://host root of a URL."""
    p = urlparse(normalize_url(url))
    return f"{p.scheme}://{p.netloc}"


def fetch_robots(url: str) -> dict:
    """Fetch and lightly parse robots.txt."""
    root = base_of(url)
    text = fetch_text(urljoin(root, "/robots.txt"))
    if text is None:
        return {"present": False, "sitemaps": [], "blocks_all": False, "raw": ""}
    sitemaps = []
    blocks_all = False
    ua_all = False
    for line in text.splitlines():
        line = line.strip()
        low = line.lower()
        if low.startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
        elif low.startswith("user-agent:"):
            ua_all = line.split(":", 1)[1].strip() == "*"
        elif ua_all and low.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path == "/":
                blocks_all = True
    return {
        "present": True,
        "sitemaps": sitemaps,
        "blocks_all": blocks_all,
        "raw": text[:2000],
    }


def fetch_sitemap(url: str, robots: dict | None = None) -> dict:
    """Locate a sitemap (from robots.txt or the default path) and count URLs."""
    root = base_of(url)
    candidates = list((robots or {}).get("sitemaps", []))
    candidates.append(urljoin(root, "/sitemap.xml"))

    for sm in candidates:
        text = fetch_text(sm)
        if text and ("<urlset" in text or "<sitemapindex" in text):
            url_count = text.count("<loc>")
            is_index = "<sitemapindex" in text
            return {"present": True, "url": sm, "url_count": url_count, "is_index": is_index}
    return {"present": False, "url": None, "url_count": 0, "is_index": False}
