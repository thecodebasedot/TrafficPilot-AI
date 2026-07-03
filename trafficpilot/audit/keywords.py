"""Keyword extraction from real page content.

A lightweight, dependency-free keyword extractor: it tokenises the visible page
text, removes stopwords, and ranks single words and two-word phrases (bigrams)
by frequency, weighting terms that appear in the title / headings. This surfaces
what the page *currently* targets so the recommendation engine can spot gaps.
"""

from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup

STOPWORDS = set(
    """a an and are as at be by for from has he in is it its of on that the to was
    were will with your you our we us this these those or not but if then so can
    all any more most other some such no nor only own same than too very s t just
    do does did have had having i me my what which who whom they them their there
    here about into over under again once new get how why when where up down out""".split()
)

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9'-]{1,}")


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS]


def extract_keywords(html: str, top_n: int = 15) -> dict:
    """Return top single-word and bigram keywords for the page."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    body_text = soup.get_text(" ", strip=True)
    emphasis = " ".join(
        t.get_text(" ", strip=True)
        for t in soup.find_all(["title", "h1", "h2", "h3", "strong", "b"])
    )

    body_tokens = _tokens(body_text)
    emph_tokens = set(_tokens(emphasis))

    # unigrams, with a x3 boost for terms used in title/headings
    unigram = Counter(body_tokens)
    for w in list(unigram):
        if w in emph_tokens:
            unigram[w] *= 3

    # bigrams
    bigrams = Counter(
        f"{a} {b}" for a, b in zip(body_tokens, body_tokens[1:])
    )

    return {
        "total_words": len(body_tokens),
        "unigrams": [
            {"term": t, "count": c} for t, c in unigram.most_common(top_n)
        ],
        "bigrams": [
            {"term": t, "count": c} for t, c in bigrams.most_common(top_n) if c > 1
        ],
    }
