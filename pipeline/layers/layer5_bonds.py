"""
Layer 5 — Bond / Survival Check
Input:  conviction-filtered tickers
Output: tickers that survive bond safety check (~15-25)
"""
from __future__ import annotations

from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.scrapers.finra_trace import get_bond_data, assign_bond_tier

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 5 error for {stock['ticker']}: {e}")
    logger.info(f"Layer 5: {len(passed)}/{len(tickers)} passed bond check")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]
    company_name = stock.get("company_name", ticker)

    bond_data = get_bond_data(company_name, ticker)
    bond_price = bond_data.get("price") if bond_data else None
    bond_tier = assign_bond_tier(bond_price)

    # Hard filter: if bonds are trading below critical threshold, skip
    # (unless company has no public debt — then assume safe)
    overhang = stock.get("net_common_overhang", 0) or 0
    has_significant_debt = overhang > stock.get("fcf_3yr_avg", 1) * 2

    if has_significant_debt and bond_tier == "critical":
        logger.debug(f"{ticker}: filtered — bonds critical ({bond_price})")
        return None

    return {
        **stock,
        "bond_price":         bond_price,
        "bond_maturity_date": bond_data.get("maturity") if bond_data else None,
        "bond_yield":         bond_data.get("yield") if bond_data else None,
        "bond_tier":          bond_tier,
        "bond_source":        bond_data.get("source") if bond_data else "unavailable",
        # FIX: pass staleness flag through so scorer can penalise stale prices
        "bond_is_stale":      bond_data.get("is_stale", False) if bond_data else False,
        "bond_trade_date":    bond_data.get("trade_date") if bond_data else None,
    }
