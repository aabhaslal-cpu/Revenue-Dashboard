"""Headline fetcher. Uses NewsAPI when a key is present, otherwise falls back
to free financial RSS feeds. Returns the top N headlines as plain strings.
"""

from __future__ import annotations

import os
import re
from typing import List
from xml.etree import ElementTree

import requests

from utils import log, log_error, retry

REQUEST_TIMEOUT = 20

# Free RSS fallbacks — no key required.
RSS_FEEDS = [
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",          # WSJ Markets
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
    "https://cointelegraph.com/rss",                          # Crypto
]

# NewsAPI query — broad market + crypto coverage.
NEWS_QUERY = (
    "stocks OR crypto OR bitcoin OR ethereum OR nvidia OR "
    "ETF OR \"interest rates\" OR \"Federal Reserve\""
)


@retry(attempts=3, base_delay=2.0, label="newsapi_fetch")
def _fetch_newsapi(api_key: str, limit: int) -> List[str]:
    resp = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "category": "business",
            "language": "en",
            "pageSize": limit,
            "apiKey": api_key,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI error: {data.get('message', 'unknown')}")
    articles = data.get("articles", [])
    return [a["title"].strip() for a in articles if a.get("title")]


@retry(attempts=3, base_delay=2.0, label="rss_fetch")
def _fetch_one_rss(url: str, limit: int) -> List[str]:
    resp = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "trading-sim-r2/1.0"},
    )
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)
    titles: List[str] = []
    for item in root.iter("item"):
        title_el = item.find("title")
        if title_el is not None and title_el.text:
            titles.append(_clean(title_el.text))
        if len(titles) >= limit:
            break
    return titles


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fetch_rss(limit: int) -> List[str]:
    headlines: List[str] = []
    for url in RSS_FEEDS:
        try:
            headlines.extend(_fetch_one_rss(url, limit))
        except Exception as exc:  # noqa: BLE001
            log_error(f"RSS feed failed: {url} — skipping", exc)
        if len(headlines) >= limit:
            break
    return headlines


def fetch_headlines(limit: int = 10) -> List[str]:
    """Return up to `limit` de-duplicated headlines. Never raises."""
    api_key = os.getenv("NEWS_API_KEY", "").strip()
    headlines: List[str] = []

    if api_key:
        try:
            headlines = _fetch_newsapi(api_key, limit)
        except Exception as exc:  # noqa: BLE001
            log_error("NewsAPI failed — falling back to RSS", exc)

    if not headlines:
        headlines = _fetch_rss(limit)

    # De-dupe preserving order, then cap.
    seen = set()
    unique: List[str] = []
    for h in headlines:
        key = h.lower()
        if h and key not in seen:
            seen.add(key)
            unique.append(h)
        if len(unique) >= limit:
            break

    if not unique:
        log_error("No headlines available from any source")
    else:
        log.info("Fetched %d headlines", len(unique))
    return unique


if __name__ == "__main__":
    for i, headline in enumerate(fetch_headlines(), 1):
        print(f"{i:2d}. {headline}")
