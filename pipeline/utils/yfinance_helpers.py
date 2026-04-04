from __future__ import annotations

import time
import yfinance as yf
import pandas as pd
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get_pickle, cache_set_pickle

logger = get_logger(__name__)

def get_ticker_info(ticker: str) -> dict:
    """Fetch ticker metadata with caching."""
    cached = cache_get_pickle("yfinance", f"info_{ticker}",
                              ttl_days=config.PRICE_CACHE_DAYS)
    if cached is not None:
        return cached
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        cache_set_pickle("yfinance", f"info_{ticker}", info)
        return info
    except Exception as e:
        logger.warning(f"yfinance info failed for {ticker}: {e}")
        return {}

def get_weekly_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch weekly OHLCV history with caching."""
    cache_key = f"weekly_{ticker}_{period}"
    cached = cache_get_pickle("yfinance", cache_key,
                              ttl_days=config.PRICE_CACHE_DAYS)
    if cached is not None:
        return cached
    try:
        df = yf.download(ticker, period=period, interval="1wk",
                         auto_adjust=True, progress=False)
        cache_set_pickle("yfinance", cache_key, df)
        return df
    except Exception as e:
        logger.warning(f"yfinance history failed for {ticker}: {e}")
        return pd.DataFrame()

def bulk_download_history(tickers: list[str],
                          period: str = "5y") -> dict[str, pd.DataFrame]:
    """Batch download for multiple tickers."""
    results = {}
    batches = [tickers[i:i+config.YFINANCE_BATCH_SIZE]
               for i in range(0, len(tickers), config.YFINANCE_BATCH_SIZE)]

    for i, batch in enumerate(batches):
        logger.info(f"Downloading batch {i+1}/{len(batches)} "
                    f"({len(batch)} tickers)")
        try:
            data = yf.download(
                " ".join(batch), period=period,
                interval="1wk", auto_adjust=True,
                progress=False, group_by="ticker"
            )
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        results[ticker] = data
                    else:
                        results[ticker] = data[ticker].dropna(how="all")
                except KeyError:
                    results[ticker] = pd.DataFrame()
        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            for ticker in batch:
                results[ticker] = pd.DataFrame()
        if i < len(batches) - 1:
            time.sleep(config.YFINANCE_SLEEP)
    return results

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI for a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float('inf'))
    return 100 - (100 / (1 + rs))
