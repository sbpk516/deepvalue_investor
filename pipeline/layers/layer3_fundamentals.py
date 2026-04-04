"""
Layer 3 — Fundamental Value Screen
Input:  list of price-filtered ticker dicts
Output: filtered list with fundamental data added (~100 tickers)
Filters: P/TBV < 1.5, positive 3yr FCF, revenue > $50M,
         overhang/FCF < 15x
"""
from __future__ import annotations

from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.edgar import get_company_facts
from pipeline.layers._fundamentals_parser import FundamentalsParser

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 3 failed for {stock['ticker']}: {e}")
    logger.info(f"Layer 3: {len(passed)}/{len(tickers)} passed fundamentals")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]
    cik = stock.get("cik")
    if not cik:
        return None

    facts = get_company_facts(cik)
    if not facts:
        return None

    parser = FundamentalsParser(facts, ticker)

    # ── Revenue check ────────────────────────────────────────
    revenue = parser.get_latest_annual("Revenues",
                  fallbacks=["RevenueFromContractWithCustomerExcludingAssessedTax",
                             "SalesRevenueNet"])
    if not revenue or revenue < config.LAYER3_MIN_REVENUE:
        return None

    # ── FCF computation ──────────────────────────────────────
    op_cf_series = parser.get_annual_series("NetCashProvidedByUsedInOperatingActivities")
    capex_series = parser.get_annual_series(
        "PaymentsToAcquirePropertyPlantAndEquipment",
        fallbacks=["CapitalExpenditureContinuingOperations"]
    )
    if not op_cf_series or len(op_cf_series) < 1:
        return None

    fcf_series = {}
    for year in op_cf_series:
        op_cf = op_cf_series[year]
        capex = capex_series.get(year, 0) or 0
        fcf_series[year] = op_cf - abs(capex)

    # 3yr average FCF
    recent_years = sorted(fcf_series.keys())[-3:]
    fcf_values = [fcf_series[y] for y in recent_years]
    fcf_3yr_avg = sum(fcf_values) / len(fcf_values)

    # Hard filter: 3yr avg FCF must be positive
    if fcf_3yr_avg <= 0:
        return None

    # ── Balance sheet ────────────────────────────────────────
    shares = parser.get_latest("CommonStockSharesOutstanding",
                 fallbacks=["EntityCommonStockSharesOutstanding"])
    if not shares or shares <= 0:
        return None

    total_assets = parser.get_latest_annual("Assets")
    total_liab   = parser.get_latest_annual("Liabilities")
    goodwill     = parser.get_latest_annual("Goodwill") or 0
    intangibles  = parser.get_latest_annual(
        "FiniteLivedIntangibleAssetsNet",
        fallbacks=["IntangibleAssetsNetExcludingGoodwill"]
    ) or 0
    cash         = parser.get_latest_annual(
        "CashAndCashEquivalentsAtCarryingValue",
        fallbacks=["CashCashEquivalentsAndShortTermInvestments"]
    ) or 0
    st_debt      = parser.get_latest_annual(
        "ShortTermBorrowings",
        fallbacks=["NotesPayableCurrent"]
    ) or 0
    lt_liab      = parser.get_latest_annual("LiabilitiesNoncurrent") or total_liab or 0

    if not total_assets or not total_liab:
        return None

    # Tangible book value
    # FIX: deferred tax assets are not tangible — must be stripped.
    # Original plan missed this. For financial companies and post-restructuring
    # companies, deferred tax assets can be 20-40% of total assets, making
    # P/TBV appear artificially low and misleadingly cheap.
    deferred_tax = parser.get_latest_annual(
        "DeferredTaxAssetsNet",
        fallbacks=["DeferredIncomeTaxAssetsNet",
                   "DeferredTaxAssetsGross"]
    ) or 0

    tangible_book = total_assets - goodwill - intangibles - deferred_tax - total_liab
    tangible_book_per_share = tangible_book / shares

    price = stock.get("price", 0)
    if price <= 0:
        return None

    ptbv = price / tangible_book_per_share if tangible_book_per_share > 0 else 999

    # Hard filter: P/TBV
    if ptbv > config.LAYER3_MAX_PTBV:
        return None

    # ── Net common overhang ──────────────────────────────────
    # Check for ASC 842 lease distortion
    op_lease_liab = parser.get_latest_annual(
        "OperatingLeaseLiability",
        fallbacks=["OperatingLeaseLiabilityNoncurrent"]
    ) or 0
    asc842_flag = False
    lease_pct = 0
    if lt_liab > 0 and op_lease_liab > 0:
        lease_pct = op_lease_liab / lt_liab
        asc842_flag = lease_pct > config.ASC842_LEASE_FLAG_PCT

    net_overhang = lt_liab + st_debt - cash
    # ASC 842 adjustment: subtract operating lease liabilities
    net_overhang_adjusted = net_overhang - op_lease_liab

    fcf_per_share = fcf_3yr_avg / shares
    fcf_yield = fcf_per_share / price

    overhang_ratio = net_overhang_adjusted / fcf_3yr_avg if fcf_3yr_avg > 0 else 999

    # Hard filter: overhang/FCF
    if overhang_ratio > config.LAYER3_MAX_OVERHANG_RATIO:
        return None

    # ── Market cap check ─────────────────────────────────────
    market_cap = price * shares

    # ── Dilution calculator ──────────────────────────────────
    dilution_pct = 0
    diluted_shares = shares
    if overhang_ratio > 8:
        target_overhang = fcf_3yr_avg * config.DILUTION_TARGET_RATIO
        excess = net_overhang_adjusted - target_overhang
        if excess > 0:
            issue_price = price * config.DILUTION_DISCOUNT
            shares_to_issue = excess / issue_price
            diluted_shares = shares + shares_to_issue
            dilution_pct = shares_to_issue / shares

    return {
        **stock,
        "market_cap":              round(market_cap),
        "revenue_ttm":             round(revenue),
        "fcf_3yr_avg":             round(fcf_3yr_avg),
        "fcf_per_share":           round(fcf_per_share, 2),
        "fcf_yield":               round(fcf_yield, 4),
        "fcf_series":              fcf_series,
        "price_to_tbv":            round(ptbv, 2),
        "tangible_book_per_share": round(tangible_book_per_share, 2),
        "net_common_overhang":     round(net_overhang_adjusted),
        "net_overhang_fcf_ratio":  round(overhang_ratio, 1),
        "asc842_flag":             asc842_flag,
        "lease_pct_of_lt_liab":    round(lease_pct, 2),
        "shares_outstanding":      shares,
        "diluted_shares":          round(diluted_shares),
        "dilution_risk_pct":       round(dilution_pct, 3),
        "cash":                    cash,
        "short_term_debt":         st_debt,
        "lt_liabilities":          lt_liab,
    }
