"""
Scrapes FINRA TRACE bond trade data for a company.
Uses Playwright for JS-rendered pages.
Falls back to a simple requests approach for some pages.
"""
from __future__ import annotations

import json
import re
import requests
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)

def get_bond_data(company_name: str, ticker: str) -> dict | None:
    """
    Fetch bond price data from FINRA.
    Returns dict with price, maturity, yield, or None if unavailable.
    """
    cache_key = f"bonds_{ticker}"
    cached = cache_get("scrapes", cache_key,
                       ttl_days=config.BOND_CACHE_DAYS)
    if cached:
        return cached if cached.get("price") else None

    if not config.ENABLE_BOND_SCRAPE:
        logger.debug(f"Bond scraping disabled, skipping {ticker}")
        return None

    result = _try_finra_api(company_name, ticker)
    if result:
        cache_set("scrapes", cache_key, result)
        return result

    result = _try_playwright(company_name, ticker)
    if result:
        cache_set("scrapes", cache_key, result)
        return result

    # Cache miss result to avoid repeated failed attempts
    cache_set("scrapes", cache_key, {"price": None, "unavailable": True})
    return None

def _try_finra_api(company_name: str, ticker: str) -> dict | None:
    """Try FINRA's public API endpoint first (faster than Playwright)."""
    try:
        url = "https://api.finra.org/data/group/otcMarket/name/tradeReport"
        params = {
            "issuerName": company_name[:30],
            "limit": 5,
            "offset": 0,
        }
        headers = {"Accept": "application/json"}
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if data:
                return _parse_finra_api_response(data[0])
    except Exception as e:
        logger.debug(f"FINRA API attempt failed for {ticker}: {e}")
    return None

def _parse_finra_api_response(item: dict) -> dict:
    price      = item.get("lastSalePrice")
    trade_date = item.get("lastSaleDate") or item.get("tradeDate")
    volume     = item.get("totalVolume", 0) or 0

    # FIX: check trade recency — stale bond prices are dangerous
    is_stale = False
    if trade_date:
        from datetime import date as _date, datetime
        try:
            td = datetime.strptime(str(trade_date)[:10], "%Y-%m-%d").date()
            days_old = (_date.today() - td).days
            is_stale = days_old > 60 or volume < 5
        except Exception:
            is_stale = True

    return {
        "price":      price,
        "yield":      item.get("yield"),
        "maturity":   item.get("maturityDate"),
        "volume":     volume,
        "trade_date": trade_date,
        "is_stale":   is_stale,
        "cusip":      item.get("cusip"),
        "source":     "FINRA API",
    }

def _try_playwright(company_name: str, ticker: str) -> dict | None:
    """
    Fallback: use Playwright to scrape FINRA bond search.
    Only runs if ENABLE_BOND_SCRAPE=true.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except ImportError:
                logger.warning(
                    "playwright-stealth not installed — FINRA scraping may "
                    "be blocked. Run: pip install playwright-stealth"
                )
            page.set_default_timeout(config.PLAYWRIGHT_TIMEOUT_MS)

            page.goto("https://finra-markets.morningstar.com/BondCenter/TRBSrkSrch.jsp")
            page.wait_for_load_state("networkidle")

            search_box = page.query_selector('input[name="IssuerName"]')
            if not search_box:
                browser.close()
                return None

            search_box.fill(company_name[:30])
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            rows = page.query_selector_all("table.tbl-data tbody tr")
            if not rows:
                browser.close()
                return None

            first_row = rows[0]
            cells = first_row.query_selector_all("td")
            if len(cells) < 6:
                browser.close()
                return None

            result = {
                "price":    _parse_price(cells[3].inner_text()),
                "yield":    _parse_price(cells[4].inner_text()),
                "maturity": cells[2].inner_text().strip(),
                "source":   "FINRA Playwright",
            }
            browser.close()
            return result if result["price"] else None

    except Exception as e:
        logger.debug(f"Playwright bond scrape failed for {ticker}: {e}")
        return None

def _parse_price(s: str) -> float | None:
    try:
        return float(re.sub(r"[^\d.]", "", s.strip()))
    except Exception:
        return None

def assign_bond_tier(price: float | None) -> str:
    if price is None:
        return "unavailable"
    if price >= config.LAYER5_BOND_SAFE:
        return "safe"
    if price >= config.LAYER5_BOND_CAUTION:
        return "caution"
    if price >= config.LAYER5_BOND_ELEVATED:
        return "elevated"
    if price >= config.LAYER5_BOND_HIGH_RISK:
        return "high_risk"
    return "critical"
