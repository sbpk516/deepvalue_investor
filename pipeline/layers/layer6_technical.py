"""
Layer 6 — Technical Confirmation
Input:  bond-checked tickers
Output: final candidates with technical signals added (~10-15)
"""
from __future__ import annotations

import json
import pandas as pd
import numpy as np
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.yfinance_helpers import (
    get_weekly_history, compute_rsi
)

logger = get_logger(__name__)

# Sector ETF mapping
with open(f"{config.DATA_DIR}sector_etf_map.json") as f:
    SECTOR_ETF_MAP = json.load(f)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    # Pre-fetch all sector ETF histories needed
    sectors_needed = {t.get("sector") for t in tickers if t.get("sector")}
    etf_histories = {}
    for sector in sectors_needed:
        etf = SECTOR_ETF_MAP.get(sector)
        if etf:
            df = get_weekly_history(etf, period="5y")
            if not df.empty:
                etf_histories[sector] = df

    results = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock, etf_histories)
            if result:
                results.append(result)
        except Exception as e:
            logger.debug(f"Layer 6 error for {stock['ticker']}: {e}")

    logger.info(f"Layer 6: {len(results)}/{len(tickers)} passed technical")
    return results

def _evaluate_ticker(stock: dict,
                     etf_histories: dict) -> dict | None:
    ticker = stock["ticker"]

    # Use cached price series from Layer 2 if available
    price_series = stock.pop("_price_series", None)
    if price_series is None or (hasattr(price_series, 'empty') and price_series.empty):
        df = get_weekly_history(ticker, period="5y")
        if df.empty:
            return stock  # pass through without technical data
        price_series = df["Close"].dropna()

    # ── Weekly RSI ───────────────────────────────────────────
    rsi_series = compute_rsi(price_series, period=14)
    current_rsi = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else None

    # RSI trend: compare last 3 weeks to prior 3 weeks
    rsi_trend = "neutral"
    weeks_improving = 0
    if len(rsi_series) >= 6:
        recent = rsi_series.iloc[-3:]
        prior  = rsi_series.iloc[-6:-3]
        if recent.mean() > prior.mean():
            rsi_trend = "improving"
            for i in range(1, min(len(rsi_series), 8)):
                if rsi_series.iloc[-i] > rsi_series.iloc[-i-1]:
                    weeks_improving += 1
                else:
                    break
        elif recent.mean() < prior.mean():
            rsi_trend = "declining"

    # ── Sector context modifier ──────────────────────────────
    sector = stock.get("sector")
    sector_modifier = 0
    sector_etf_3yr_return = None
    stock_3yr_return = stock.get("pct_below_3yr_high", None)

    if sector and sector in etf_histories:
        etf_df = etf_histories[sector]
        etf_close = etf_df["Close"].dropna()
        if len(etf_close) >= 156:
            etf_now   = float(etf_close.iloc[-1])
            etf_3yr   = float(etf_close.iloc[-156])
            sector_etf_3yr_return = (etf_now - etf_3yr) / etf_3yr

            if sector_etf_3yr_return < -0.20:
                sector_modifier = config.SECTOR_DOWN_BONUS
            elif sector_etf_3yr_return > 0.20:
                sector_modifier = config.SECTOR_UP_PENALTY

    # ── Support retest ───────────────────────────────────────
    support_retest = False
    if len(price_series) >= 52:
        low_52 = float(price_series.iloc[-52:].min())
        current = float(price_series.iloc[-1])
        prev_4wk_min = float(price_series.iloc[-8:-4].min())
        if prev_4wk_min <= low_52 * 1.05 and current > prev_4wk_min * 1.10:
            support_retest = True

    # ── Decline type classification ──────────────────────────
    decline_type = _classify_decline(stock)

    return {
        **stock,
        "rsi_weekly":             round(current_rsi, 1) if current_rsi else None,
        "rsi_trend":              rsi_trend,
        "weeks_rsi_improving":    weeks_improving,
        "support_retest":         support_retest,
        "sector_etf_3yr_return":  round(sector_etf_3yr_return, 3) if sector_etf_3yr_return else None,
        "stock_3yr_return":       round(stock_3yr_return, 3) if stock_3yr_return else None,
        "sector_context_modifier": sector_modifier,
        "decline_type":           decline_type,
    }

def _classify_decline(stock: dict) -> str:
    """Classify decline as cyclical, secular, or mixed."""
    import json as _json
    try:
        with open(f"{config.DATA_DIR}secular_decline_sic.json") as f:
            secular_sics = set(_json.load(f))
        with open(f"{config.DATA_DIR}cyclical_sic.json") as f:
            cyclical_sics = set(_json.load(f))
    except FileNotFoundError:
        return "unknown"

    sic = stock.get("sic_code", "")
    if sic in secular_sics:
        return "secular"
    if sic in cyclical_sics:
        return "cyclical"

    fcf_series = stock.get("fcf_series", {})
    if len(fcf_series) >= 5:
        years = sorted(fcf_series.keys())
        values = [fcf_series[y] for y in years]
        if values[0] > 0 and values[-1] > 0:
            return "cyclical"
        if all(v <= 0 for v in values[-3:]):
            return "secular"

    return "mixed"
