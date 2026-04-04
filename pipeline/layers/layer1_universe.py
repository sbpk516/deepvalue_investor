"""
Layer 1 — Universe Fetch
Input:  config dict
Output: list of {"ticker": str, "cik": str, ...} dicts (~6,000)
"""
from __future__ import annotations

import requests
import json
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)
HEADERS = {"User-Agent": "RK-Screener research@example.com"}

def run(input_data: dict, cfg: dict, market: str = "US") -> list[dict]:
    """Fetch universe of US-listed stocks from SEC EDGAR."""
    cached = cache_get("universe", "us_tickers",
                       ttl_days=config.UNIVERSE_CACHE_DAYS)
    if cached:
        logger.info(f"Universe loaded from cache: {len(cached)} tickers")
        return cached

    logger.info("Fetching universe from SEC EDGAR...")
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            headers=HEADERS, timeout=60
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch universe: {e}")
        return []

    tickers = []
    raw_data = raw.get("data", [])

    # FIX: validate response format before processing.
    # This endpoint has changed format twice historically.
    # Expected: list of [cik, name, ticker, exchange] lists.
    # Catch format changes early with a clear error message.
    if not raw_data:
        logger.error("EDGAR company_tickers_exchange.json returned empty data")
        return []
    if not isinstance(raw_data[0], list) or len(raw_data[0]) < 4:
        logger.error(
            f"EDGAR company_tickers_exchange.json format changed! "
            f"Expected list of [cik,name,ticker,exchange], "
            f"got: {raw_data[0]}. Update layer1_universe.py to match."
        )
        return []

    for item in raw_data:
        # Format: [cik, name, ticker, exchange]
        if len(item) >= 4 and item[3] in ("Nasdaq", "NYSE", "NYSE MKT"):
            tickers.append({
                "ticker":       item[2].upper(),
                "company_name": item[1],
                "cik":          str(item[0]).zfill(10),
                "exchange":     item[3],
            })

    logger.info(f"Universe: {len(tickers)} tickers from EDGAR")
    cache_set("universe", "us_tickers", tickers)
    return tickers
