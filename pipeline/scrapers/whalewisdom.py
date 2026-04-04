"""
Scrapes WhaleWisdom for institutional holders,
cross-references against known value funds list.
"""
from __future__ import annotations

import json
import requests
from bs4 import BeautifulSoup
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
}

def load_value_funds() -> list[dict]:
    with open(f"{config.DATA_DIR}value_funds.json") as f:
        return json.load(f)

VALUE_FUNDS = load_value_funds()
VALUE_FUND_NAMES = {f["fund_name"].lower() for f in VALUE_FUNDS}

def get_institutional_holders(ticker: str) -> list[dict]:
    """
    Get top institutional holders and flag known value funds.

    FIX: WhaleWisdom requires JavaScript to render the holders table.
    Phase 1 uses yfinance institutional_holders only.
    WhaleWisdom via Playwright is deferred to Phase 2.
    """
    cache_key = f"inst_{ticker}"
    cached = cache_get("scrapes", cache_key, ttl_days=7)
    if cached:
        return cached.get("data", [])

    holders = _parse_yf_holders(ticker)

    # Flag known value funds
    for h in holders:
        name_lower = h.get("holder_name", "").lower()
        h["is_value_fund"] = any(
            vf in name_lower for vf in VALUE_FUND_NAMES
        )

    cache_set("scrapes", cache_key, {"data": holders})
    return holders

def _parse_yf_holders(ticker: str) -> list[dict]:
    """Parse institutional holders from yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.institutional_holders
        if df is None or df.empty:
            return []
        holders = []
        for _, row in df.iterrows():
            holders.append({
                "holder_name":  str(row.get("Holder", "")),
                "pct_held":     float(row.get("% Out", 0)),
                "shares_held":  int(row.get("Shares", 0)),
                "value_usd":    float(row.get("Value", 0)),
                "recent_change": None,
                "is_value_fund": False,
            })
        return holders
    except Exception as e:
        logger.debug(f"yfinance holders failed for {ticker}: {e}")
        return []

def _scrape_whalewisdom(ticker: str) -> list[dict]:
    """
    FIX: WhaleWisdom requires JavaScript to render the holders table.
    Phase 1: placeholder that always returns empty list.
    Phase 2: replace with Playwright + playwright-stealth.
    """
    logger.debug(f"WhaleWisdom requires Playwright — deferred to Phase 2 for {ticker}")
    return []

def _parse_pct(s: str) -> float:
    try:
        return float(s.replace("%", "").replace(",", "").strip()) / 100
    except Exception:
        return 0.0

def get_best_value_fund_holder(ticker: str) -> dict | None:
    """Return the largest known value fund holder if any."""
    holders = get_institutional_holders(ticker)
    value_holders = [h for h in holders if h.get("is_value_fund")]
    if not value_holders:
        return None
    return max(value_holders, key=lambda h: h.get("pct_held", 0))
