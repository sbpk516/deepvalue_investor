"""Generates plain-English risk flags for a stock."""
from __future__ import annotations

from pipeline import config

FLAG_PRIORITY = {
    "bond_caution": 1, "bond_high_risk": 2, "asc842": 3,
    "short_maturity": 4, "high_dilution": 5, "no_value_fund": 6,
    "rsi_unconfirmed": 7, "secular_decline": 8, "fcf_weak": 9,
    "low_insider_own": 10,
}

class RiskFlagGenerator:
    def generate(self, stock: dict, components: dict) -> list[dict]:
        flags = []

        bond_tier = stock.get("bond_tier", "unavailable")
        if bond_tier == "caution":
            flags.append({"key": "bond_caution", "severity": "warning",
                "text": f"Bonds at {stock.get('bond_price', '?'):.0f} — "
                        f"caution zone. Read debt footnote in latest 10-Q."})
        elif bond_tier in ("elevated", "high_risk"):
            flags.append({"key": "bond_high_risk", "severity": "danger",
                "text": f"Bonds at {stock.get('bond_price', '?'):.0f} — "
                        f"elevated risk. Verify covenant compliance."})

        if stock.get("asc842_flag"):
            flags.append({"key": "asc842", "severity": "info",
                "text": (f"Operating leases are "
                         f"{stock.get('lease_pct_of_lt_liab', 0):.0%} of "
                         f"long-term liabilities (ASC 842). "
                         f"Net overhang may overstate debt.")})

        maturity = stock.get("bond_maturity_date")
        if maturity and _months_until(maturity) < 18:
            flags.append({"key": "short_maturity", "severity": "warning",
                "text": f"Bond matures {maturity} — "
                        f"refinancing risk in near term."})

        if stock.get("dilution_risk_pct", 0) > 0.20:
            flags.append({"key": "high_dilution", "severity": "warning",
                "text": f"High leverage — potential "
                        f"{stock['dilution_risk_pct']:.0%} dilution if "
                        f"equity raise needed."})

        if not stock.get("value_fund_name"):
            flags.append({"key": "no_value_fund", "severity": "note",
                "text": "No known value fund holders detected in 13F data."})

        rsi = stock.get("rsi_weekly")
        if rsi and rsi > 35 and stock.get("rsi_trend") != "improving":
            flags.append({"key": "rsi_unconfirmed", "severity": "note",
                "text": "Technical trend not confirmed — "
                        "RSI not yet recovering from oversold."})

        if stock.get("decline_type") == "secular":
            flags.append({"key": "secular_decline", "severity": "warning",
                "text": "Industry shows signs of secular decline — "
                        "verify recovery thesis carefully."})

        if stock.get("insider_ownership_pct", 0) < 0.08:
            flags.append({"key": "low_insider_own", "severity": "note",
                "text": f"Insider ownership "
                        f"{stock.get('insider_ownership_pct', 0):.1%} — "
                        f"below RK's 20% preference."})

        flags.sort(key=lambda f: FLAG_PRIORITY.get(f["key"], 99))
        return flags

def _months_until(date_str: str) -> int:
    from datetime import date, datetime
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (d - date.today()).days // 30
    except Exception:
        return 99
