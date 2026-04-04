"""
Layer 2 — Price Pain Screen
Input:  list of ticker dicts from Layer 1
Output: filtered list with price data added (~400 tickers)
Filter: stock down 40%+ from 3yr high
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.yfinance_helpers import (
    bulk_download_history, get_ticker_info
)

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    symbols = [t["ticker"] for t in tickers]
    ticker_map = {t["ticker"]: t for t in tickers}

    logger.info(f"Downloading 5yr weekly history for {len(symbols)} tickers...")
    histories = bulk_download_history(symbols, period="5y")

    passed = []
    failed_count = 0

    for ticker, df in histories.items():
        try:
            result = _evaluate_ticker(ticker, df, ticker_map.get(ticker, {}))
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 2 failed for {ticker}: {e}")
            failed_count += 1

    logger.info(f"Layer 2: {len(passed)} passed, "
                f"{len(symbols)-len(passed)-failed_count} filtered, "
                f"{failed_count} errors")
    return passed

def _evaluate_ticker(ticker: str, df: pd.DataFrame,
                     base_data: dict) -> dict | None:
    if df.empty or len(df) < 52:  # need at least 1yr of weekly data
        return None

    close = df["Close"].dropna()
    if len(close) < 52:
        return None

    current_price = float(close.iloc[-1])
    if current_price <= 0:
        return None

    # 3yr high (156 weeks)
    lookback = min(len(close), 156)
    high_3yr = float(close.iloc[-lookback:].max())

    pct_below_3yr_high = (current_price - high_3yr) / high_3yr
    # Negative number — e.g. -0.67 means down 67%

    # Hard filter: must be down at least LAYER2_MIN_DRAWDOWN_PCT
    threshold = -config.LAYER2_MIN_DRAWDOWN_PCT / 100
    if pct_below_3yr_high > threshold:
        return None

    # 52wk low proximity (how close to 52wk low?)
    low_52wk = float(close.iloc[-52:].min())
    pct_above_52wk_low = (current_price - low_52wk) / low_52wk

    return {
        **base_data,
        "ticker":               ticker,
        "price":                round(current_price, 2),
        "high_3yr":             round(high_3yr, 2),
        "pct_below_3yr_high":   round(pct_below_3yr_high, 4),
        "pct_above_52wk_low":   round(pct_above_52wk_low, 4),
        "low_52wk":             round(low_52wk, 2),
        "price_history_weeks":  len(close),
        "_price_series":        close,   # kept for Layer 6 RSI; stripped before JSON output
    }
