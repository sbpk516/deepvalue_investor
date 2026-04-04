"""
Layer 4 — Conviction Signals
Input:  fundamentals-filtered tickers
Output: tickers with insider buy OR value fund holder (~30 tickers)
"""
from __future__ import annotations

from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.scrapers.openinsider import get_best_insider_buy
from pipeline.scrapers.whalewisdom import (
    get_best_value_fund_holder, get_institutional_holders
)
from pipeline.utils.yfinance_helpers import get_ticker_info

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 4 error for {stock['ticker']}: {e}")
    logger.info(f"Layer 4: {len(passed)}/{len(tickers)} passed conviction")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]

    # ── Insider ownership % ──────────────────────────────────
    info = get_ticker_info(ticker)
    insider_own_pct = info.get("heldPercentInsiders", 0) or 0

    # ── Insider buying ───────────────────────────────────────
    best_buy = get_best_insider_buy(ticker)

    # ── Institutional holders ────────────────────────────────
    best_vf = get_best_value_fund_holder(ticker)

    # ── Pass/fail logic (OR — either qualifies) ──────────────
    passes_insider = (best_buy is not None and
                      best_buy.get("value", 0) >= config.LAYER4_MIN_INSIDER_BUY)
    passes_value_fund = (best_vf is not None and
                         best_vf.get("pct_held", 0) >= 0.05)
    passes_insider_own = insider_own_pct >= 0.20

    if not (passes_insider or passes_value_fund or passes_insider_own):
        return None

    # ── Compute insider buy vs compensation ratio ────────────
    ins_vs_comp = None
    if best_buy:
        annual_comp_proxy = info.get("totalPay", None)
        if annual_comp_proxy and annual_comp_proxy > 0:
            ins_vs_comp = best_buy["value"] / annual_comp_proxy

    return {
        **stock,
        "insider_buy_amount":    best_buy["value"] if best_buy else None,
        "insider_buy_role":      best_buy["title"] if best_buy else None,
        "insider_buy_date":      best_buy["trade_date"] if best_buy else None,
        "insider_buy_name":      best_buy["name"] if best_buy else None,
        "insider_buy_count":     1 if best_buy else 0,
        "insider_pct_of_comp":   round(ins_vs_comp, 2) if ins_vs_comp else None,
        "insider_is_ceo_cfo":    best_buy.get("is_ceo_cfo_chairman", False) if best_buy else False,
        # FIX: pass 10b5-1 flag through so scorer can halve base points
        "insider_is_10b51_plan": best_buy.get("is_10b51_plan", False) if best_buy else False,
        "value_fund_name":       best_vf["holder_name"] if best_vf else None,
        "value_fund_pct":        best_vf["pct_held"] if best_vf else None,
        "insider_ownership_pct": round(insider_own_pct, 3),
        "short_interest_pct":    info.get("shortPercentOfFloat", None),
    }
