"""Price fetcher across crypto (CoinGecko), stocks and ETFs (yfinance).

Each asset is fetched independently — a failure on one asset is logged and
skipped rather than aborting the whole run.
"""

from __future__ import annotations

import os
from typing import Dict

import requests

from utils import log, log_error, retry

# --------------------------------------------------------------------------- #
# Universe — the agent has full discretion, but these are the scanned tickers.
# --------------------------------------------------------------------------- #
# CoinGecko uses internal ids, so map our tickers to them.
CRYPTO_IDS: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "HYPE": "hyperliquid",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "SUI": "sui",
}

STOCKS = ["NVDA", "RKLB"]
ETFS = ["SPY", "QQQ", "OIH", "SLV", "GLD", "ARKK"]

REQUEST_TIMEOUT = 20


def _coingecko_base_and_headers() -> tuple[str, dict]:
    """Return (base_url, headers) honoring the configured CoinGecko tier."""
    api_key = os.getenv("COINGECKO_API_KEY", "").strip()
    tier = os.getenv("COINGECKO_API_TIER", "demo").strip().lower()
    if api_key and tier == "pro":
        return "https://pro-api.coingecko.com/api/v3", {"x-cg-pro-api-key": api_key}
    if api_key:
        return "https://api.coingecko.com/api/v3", {"x-cg-demo-api-key": api_key}
    # No key — use the free public endpoint (lower rate limits).
    return "https://api.coingecko.com/api/v3", {}


@retry(attempts=3, base_delay=2.0, label="coingecko_fetch")
def _fetch_crypto_raw() -> dict:
    base, headers = _coingecko_base_and_headers()
    ids = ",".join(CRYPTO_IDS.values())
    resp = requests.get(
        f"{base}/simple/price",
        params={
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_crypto_prices() -> Dict[str, dict]:
    """Return {TICKER: {price, change_24h}} for crypto. Skips failures."""
    out: Dict[str, dict] = {}
    try:
        raw = _fetch_crypto_raw()
    except Exception as exc:  # noqa: BLE001
        log_error("Crypto price fetch failed entirely", exc)
        return out

    for ticker, cg_id in CRYPTO_IDS.items():
        entry = raw.get(cg_id)
        if not entry or "usd" not in entry:
            log_error(f"Crypto price missing for {ticker} ({cg_id}) — skipping")
            continue
        out[ticker] = {
            "price": round(float(entry["usd"]), 6),
            "change_24h": round(float(entry.get("usd_24h_change", 0.0)), 2),
            "asset_class": "crypto",
        }
    return out


@retry(attempts=3, base_delay=2.0, label="yfinance_fetch")
def _fetch_stock_raw(ticker: str) -> dict:
    # Imported lazily so a missing yfinance only breaks equities, not crypto.
    import yfinance as yf

    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d")
    if hist.empty:
        raise ValueError(f"No history returned for {ticker}")

    last_close = float(hist["Close"].iloc[-1])
    if len(hist) >= 2:
        prev_close = float(hist["Close"].iloc[-2])
        change = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
    else:
        change = 0.0
    return {"price": round(last_close, 4), "change_24h": round(change, 2)}


def fetch_equity_prices() -> Dict[str, dict]:
    """Return {TICKER: {price, change_24h, asset_class}} for stocks + ETFs."""
    out: Dict[str, dict] = {}
    for ticker in STOCKS + ETFS:
        asset_class = "stock" if ticker in STOCKS else "etf"
        try:
            data = _fetch_stock_raw(ticker)
            data["asset_class"] = asset_class
            out[ticker] = data
        except Exception as exc:  # noqa: BLE001
            log_error(f"Equity price fetch failed for {ticker} — skipping", exc)
    return out


def fetch_all_prices() -> Dict[str, dict]:
    """Aggregate every asset class into one dict keyed by ticker."""
    prices: Dict[str, dict] = {}
    prices.update(fetch_crypto_prices())
    prices.update(fetch_equity_prices())
    log.info("Fetched %d/%d prices", len(prices),
             len(CRYPTO_IDS) + len(STOCKS) + len(ETFS))
    return prices


if __name__ == "__main__":
    from pprint import pprint

    pprint(fetch_all_prices())
