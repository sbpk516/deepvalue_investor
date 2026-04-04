"""
Scrapes OpenInsider.com for open-market insider purchases.
Returns structured insider buying data per ticker.
"""
from __future__ import annotations

import time
import pandas as pd
import requests
from datetime import date, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

import random

logger = get_logger(__name__)

OPENINSIDER_URL = "http://openinsider.com/screener"

# FIX: rotate User-Agent strings — single static UA gets Cloudflare-blocked
# within days of regular nightly use.
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def _get_headers() -> dict:
    return {
        "User-Agent":      random.choice(_USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer":         "https://openinsider.com/",
    }

# Role codes that RK cares about
PRIORITY_ROLES = {
    "CEO": 30, "Chief Executive Officer": 30,
    "CFO": 25, "Chief Financial Officer": 25,
    "Chairman": 25, "Executive Chairman": 25,
    "President": 20,
    "COO": 15, "Chief Operating Officer": 15,
    "Director": 10,
    "VP": 8, "Vice President": 8,
}

def get_insider_buys(ticker: str, days_back: int = 180) -> list[dict]:
    """
    Fetch open-market purchases for a ticker from OpenInsider.
    Returns list of purchase dicts sorted by value descending.
    Falls back to EDGAR Form 4 parsing if OpenInsider is blocked.
    """
    cache_key = f"insider_{ticker}_{days_back}"
    cached = cache_get("scrapes", cache_key, ttl_days=1)
    if cached:
        return cached.get("data", [])

    start = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "s":         ticker,
        "tt":        "P",           # P = Purchase (open market only)
        "minprice":  "10000",
        "daterange": "custom",
        "startdate": start,
        "enddate":   date.today().strftime("%Y-%m-%d"),
    }
    try:
        # FIX: random delay reduces bot detection probability
        time.sleep(random.uniform(2.0, 5.0))
        r = requests.get(OPENINSIDER_URL, params=params,
                         headers=_get_headers(), timeout=30)

        # FIX: handle Cloudflare block — fall back to EDGAR
        if r.status_code in (403, 429, 503):
            logger.warning(f"OpenInsider blocked ({r.status_code}) for "
                           f"{ticker} — falling back to EDGAR Form 4")
            return _get_insider_buys_from_edgar(ticker, days_back)

        r.raise_for_status()
        tables = pd.read_html(r.text)
        if not tables:
            cache_set("scrapes", cache_key, {"data": []})
            return []

        df = tables[0]

        # FIX: validate expected columns exist before processing rows.
        # Table structure changes are a 0-warning silent failure otherwise.
        required_cols = {"Title", "Value"}
        if not required_cols.issubset(set(df.columns)):
            logger.warning(f"OpenInsider table structure changed for "
                           f"{ticker} — found columns: {list(df.columns)[:8]}. "
                           f"Falling back to EDGAR.")
            return _get_insider_buys_from_edgar(ticker, days_back)

    except Exception as e:
        logger.debug(f"OpenInsider scrape failed for {ticker}: {e}")
        return _get_insider_buys_from_edgar(ticker, days_back)

    buys = []
    for _, row in df.iterrows():
        try:
            buy = _parse_row(row)
            if buy:
                buys.append(buy)
        except Exception:
            continue

    # Sort by value descending
    buys.sort(key=lambda x: x.get("value", 0), reverse=True)
    cache_set("scrapes", cache_key, {"data": buys})
    return buys

def _get_insider_buys_from_edgar(ticker: str, days_back: int) -> list[dict]:
    """
    Fallback: find Form 4 filings via EDGAR full-text search.
    """
    from pipeline.utils.edgar import search_filings
    try:
        filings = search_filings(ticker, ["4"], days_back=days_back)
        buys = []
        for filing in filings[:20]:
            source = filing.get("_source", {})
            buys.append({
                "ticker":               ticker,
                "name":                 source.get("entity_name", ""),
                "title":                "Unknown — EDGAR fallback",
                "role_score":           0,
                "trade_date":           source.get("period_of_report", ""),
                "value":                0,
                "is_ceo_cfo_chairman":  False,
                "is_10b51_plan":        False,
                "source":               "EDGAR Form 4 fallback",
            })
        return buys
    except Exception as e:
        logger.debug(f"EDGAR Form 4 fallback also failed for {ticker}: {e}")
        return []


def _parse_row(row) -> dict | None:
    """Parse a single OpenInsider table row."""
    try:
        title = str(row.get("Title", row.get(4, "")))
        role_score = 0
        for role_name, score in PRIORITY_ROLES.items():
            if role_name.lower() in title.lower():
                role_score = score
                break
        if role_score == 0:
            return None

        val_raw = str(row.get("Value", row.get(9, "0")))
        val_clean = val_raw.replace("$", "").replace(",", "").strip()
        value = float(val_clean) if val_clean else 0

        if value < 10_000:
            return None

        date_raw = str(row.get("Trade\xa0Date", row.get(1, "")))

        # FIX: detect 10b5-1 plan purchases
        row_text = " ".join(str(v) for v in row.values()).lower()
        is_10b51 = "10b5" in row_text or "rule 10b5" in row_text

        return {
            "ticker":              str(row.get("Ticker", "")),
            "name":                str(row.get("Insider Name", row.get(3, ""))),
            "title":               title,
            "role_score":          role_score,
            "trade_date":          date_raw,
            "value":               value,
            "is_ceo_cfo_chairman": role_score >= 25,
            "is_10b51_plan":       is_10b51,
        }
    except Exception:
        return None

def get_best_insider_buy(ticker: str) -> dict | None:
    """Return the highest-value relevant insider buy in last 180 days."""
    buys = get_insider_buys(ticker)
    if not buys:
        return None
    significant = [b for b in buys if b["value"] >= config.LAYER4_MIN_INSIDER_BUY]
    if not significant:
        return None
    return significant[0]
