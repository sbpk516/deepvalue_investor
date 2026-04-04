"""Computes conservative and bull-case upside multiples."""
from pipeline import config

class UpsideCalc:
    def calculate(self, stock: dict) -> dict:
        price = stock.get("price", 0)
        if not price or price <= 0:
            return {"conservative": None, "bull": None, "diluted": None}

        shares = stock.get("shares_outstanding", 1) or 1
        fcf_3yr = stock.get("fcf_3yr_avg", 0) or 0
        diluted_shares = stock.get("diluted_shares", shares) or shares

        # Peak FCF from historical series
        fcf_series = stock.get("fcf_series", {})
        peak_fcf = max(fcf_series.values()) if fcf_series else fcf_3yr

        norm_fcf_per_share  = fcf_3yr / shares
        peak_fcf_per_share  = peak_fcf / shares
        diluted_fcf_per_share = fcf_3yr / diluted_shares

        conservative_target = norm_fcf_per_share * config.UPSIDE_CONSERVATIVE_MULTIPLE
        bull_target         = peak_fcf_per_share * config.UPSIDE_BULL_MULTIPLE
        diluted_target      = diluted_fcf_per_share * config.UPSIDE_CONSERVATIVE_MULTIPLE

        return {
            "conservative": round(conservative_target / price, 1) if price else None,
            "bull":         round(bull_target / price, 1) if price else None,
            "diluted":      round(diluted_target / price, 1) if price else None,
            "dilution_pct": round(stock.get("dilution_risk_pct", 0), 3),
        }
