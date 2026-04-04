"""RK Confidence Scorer — implements RK's buy criteria."""
from pipeline import config
from pipeline.scoring.base_scorer import BaseScorer
from pipeline.scoring.transparency import TransparencyBuilder
from pipeline.scoring.upside_calc import UpsideCalc
from pipeline.scoring.risk_flags import RiskFlagGenerator
from pipeline.scoring.action_steps import ActionStepGenerator
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

class RKScorer(BaseScorer):
    def score(self, stock: dict,
              weights_override: dict = None) -> dict:
        components = {
            "insider":       self._score_insider(stock),
            "bonds":         self._score_bonds(stock),
            "fcf":           self._score_fcf(stock),
            "institutional": self._score_institutional(stock),
            "technical":     self._score_technical(stock),
        }

        sector_mod = stock.get("sector_context_modifier", 0)
        base_total = sum(c["points"] for c in components.values())
        total = min(100, max(0, base_total + sector_mod))

        tier = self._get_tier(total)
        upside = UpsideCalc().calculate(stock)
        risk_flags = RiskFlagGenerator().generate(stock, components)
        action_steps = ActionStepGenerator().generate(stock, components)
        top_signal = self._get_top_signal(components, stock)
        transparency = TransparencyBuilder().build(
            stock, components, sector_mod, total
        )

        return {
            "score_total":         round(total, 1),
            "score_tier":          tier["label"],
            "score_label":         tier["plain_label"],
            "score_color":         tier["color"],
            "sector_modifier":     sector_mod,
            "components":          components,
            "transparency":        transparency,
            "conservative_upside": upside["conservative"],
            "bull_upside":         upside["bull"],
            "diluted_upside":      upside["diluted"],
            "dilution_risk_pct":   upside.get("dilution_pct", 0),
            "risk_flags":          risk_flags,
            "action_steps":        action_steps,
            "top_signal":          top_signal,
            "suggested_position":  tier["suggested_position"],
        }

    def _score_insider(self, stock: dict) -> dict:
        pts = 0
        reasoning = "No recent insider buying detected"
        detail = {}

        buy_amount  = stock.get("insider_buy_amount") or 0
        is_ceo_cfo  = stock.get("insider_is_ceo_cfo", False)
        at_low      = stock.get("insider_at_3yr_low", False)
        pct_comp    = stock.get("insider_pct_of_comp") or 0
        is_10b51    = stock.get("insider_is_10b51_plan", False)

        if buy_amount >= 2_000_000 or stock.get("insider_buy_count", 0) >= 3:
            pts = 30
            reasoning = f"Very large insider buy: ${buy_amount:,.0f}"
        elif buy_amount >= 500_000 and is_ceo_cfo:
            pts = 22
            reasoning = f"CEO/CFO buy: ${buy_amount:,.0f}"
        elif buy_amount >= 200_000 and is_ceo_cfo:
            pts = 15
            reasoning = f"CEO/CFO buy: ${buy_amount:,.0f}"
        elif buy_amount >= 50_000:
            pts = 8
            reasoning = f"Director buy: ${buy_amount:,.0f}"

        # FIX: halve base points for 10b5-1 plan purchases
        if is_10b51 and pts > 0:
            pts = pts // 2
            reasoning += " (10b5-1 pre-scheduled plan — weaker signal)"

        bonus_at_low = 0
        bonus_comp   = 0
        if pts > 0:
            pct_above_low = stock.get("pct_above_52wk_low", 1.0)
            if pct_above_low is not None and pct_above_low < 0.20:
                bonus_at_low = 5
                reasoning += " — at 3yr low"

            if pct_comp and pct_comp > 0.80:
                bonus_comp = 2
                reasoning += f" ({pct_comp:.0%} of annual comp)"

        pts = self._cap_component(pts + bonus_at_low + bonus_comp, "insider")
        detail = {
            "base_points":    min(pts, 30),
            "bonus_at_low":   bonus_at_low,
            "bonus_comp":     bonus_comp,
            "is_10b51":       is_10b51,
            "buy_amount":     buy_amount,
            "buyer_role":     stock.get("insider_buy_role"),
            "buyer_name":     stock.get("insider_buy_name"),
            "buy_date":       stock.get("insider_buy_date"),
        }
        short = (f"{stock.get('insider_buy_role','Insider')} bought "
                 f"${buy_amount:,.0f}" if buy_amount else "No insider buy")

        return {"points": pts, "max": 30, "reasoning": reasoning,
                "reasoning_short": short, "detail": detail}

    def _score_bonds(self, stock: dict) -> dict:
        pts = 0
        tier    = stock.get("bond_tier", "unavailable")
        price   = stock.get("bond_price")
        ratio   = stock.get("net_overhang_fcf_ratio", 0) or 0
        asc842  = stock.get("asc842_flag", False)
        is_stale = stock.get("bond_is_stale", False)

        if tier == "unavailable":
            pts = 25 if ratio < 2 else 15
            reasoning = "No public bonds — low leverage confirmed" if ratio < 2 \
                        else "No bond data available"
        elif tier == "safe":
            pts = 25 if ratio < 5 else 20
            reasoning = f"Bonds at {price:.0f} — safe zone"
        elif tier == "caution":
            pts = 18
            reasoning = f"Bonds at {price:.0f} — caution zone"
        elif tier == "elevated":
            pts = 10
            reasoning = f"Bonds at {price:.0f} — elevated risk"
        elif tier == "high_risk":
            pts = 4
            reasoning = f"Bonds at {price:.0f} — high risk"
        else:  # critical
            pts = 0
            reasoning = f"Bonds at {price:.0f} — critical"

        if asc842:
            pts = max(0, pts - 3)
            reasoning += " (ASC 842 lease distortion — adjusted)"

        # FIX: penalise stale bond prices
        if is_stale and tier not in ("unavailable",):
            pts = max(0, pts - 5)
            trade_date = stock.get("bond_trade_date", "unknown date")
            reasoning += f" — price may be stale (last trade: {trade_date})"

        pts = self._cap_component(pts, "bonds")
        short = reasoning[:60]
        return {"points": pts, "max": 25, "reasoning": reasoning,
                "reasoning_short": short,
                "detail": {"bond_price": price, "bond_tier": tier,
                           "overhang_ratio": ratio, "asc842": asc842,
                           "is_stale": is_stale}}

    def _score_fcf(self, stock: dict) -> dict:
        pts = 0
        fcf_yield = stock.get("fcf_yield", 0) or 0
        ptbv = stock.get("price_to_tbv", 99) or 99
        consec = stock.get("fcf_consecutive_positive_years", 0) or 0

        if fcf_yield >= 0.25 or (fcf_yield >= 0.15 and ptbv < 0.5):
            pts = 20
        elif fcf_yield >= 0.15 or ptbv < 0.5:
            pts = 14
        elif fcf_yield >= 0.10 or ptbv < 1.0:
            pts = 10
        elif fcf_yield >= 0.05:
            pts = 8
        elif fcf_yield > 0:
            pts = 2

        bonus = 3 if consec >= 5 else 0
        pts = self._cap_component(pts + bonus, "fcf")
        reasoning = (f"FCF yield {fcf_yield:.1%}, P/TBV {ptbv:.2f}"
                     if ptbv < 99 else f"FCF yield {fcf_yield:.1%}")
        return {"points": pts, "max": 20, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"fcf_yield": fcf_yield, "ptbv": ptbv,
                           "consecutive_positive": consec}}

    def _score_institutional(self, stock: dict) -> dict:
        pts = 0
        fund = stock.get("value_fund_name")
        pct  = stock.get("value_fund_pct", 0) or 0
        added = stock.get("value_fund_added", False)
        insider_own = stock.get("insider_ownership_pct", 0) or 0

        if fund and pct >= 0.05 and added:
            pts = 15
            reasoning = f"{fund} holds {pct:.1%} (recently added)"
        elif fund and pct >= 0.05:
            pts = 10
            reasoning = f"{fund} holds {pct:.1%}"
        elif insider_own >= 0.20:
            pts = 8
            reasoning = f"Insider ownership {insider_own:.1%}"
        elif fund:
            pts = 5
            reasoning = f"{fund} holds a stake"
        else:
            pts = 2
            reasoning = "No notable value fund holders"

        pts = self._cap_component(pts, "institutional")
        return {"points": pts, "max": 15, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"value_fund": fund, "pct_held": pct,
                           "recently_added": added,
                           "insider_own": insider_own}}

    def _score_technical(self, stock: dict) -> dict:
        pts = 0
        rsi = stock.get("rsi_weekly")
        trend = stock.get("rsi_trend", "neutral")
        weeks = stock.get("weeks_rsi_improving", 0)
        retest = stock.get("support_retest", False)

        if rsi and rsi < 30 and trend == "improving" and weeks >= 3:
            pts = 10
        elif rsi and rsi < 35 and trend == "improving":
            pts = 7
        elif trend == "improving":
            pts = 5
        elif trend == "neutral":
            pts = 4
        else:
            pts = 1

        if retest:
            pts = min(pts + 2, 10)

        pts = self._cap_component(pts, "technical")
        reasoning = (f"RSI {rsi:.0f}, {trend}"
                     if rsi else f"RSI unavailable, {trend}")
        if weeks > 0:
            reasoning += f" {weeks} weeks"
        return {"points": pts, "max": 10, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"rsi": rsi, "trend": trend,
                           "weeks_improving": weeks, "support_retest": retest}}

    def _get_tier(self, score: float) -> dict:
        if score >= config.TIER_EXCEPTIONAL:
            return {"label": "Exceptional",
                    "plain_label": "Very strong buy signal",
                    "suggested_position": "4-6%",
                    "color": "exceptional"}
        elif score >= config.TIER_HIGH_CONVICTION:
            return {"label": "High Conviction",
                    "plain_label": "Strong buy signal",
                    "suggested_position": "3-4%",
                    "color": "high_conviction"}
        elif score >= config.TIER_SPECULATIVE:
            return {"label": "Speculative",
                    "plain_label": "Worth a small position",
                    "suggested_position": "1-2%",
                    "color": "speculative"}
        else:
            return {"label": "Watch Only",
                    "plain_label": "Not yet — keep watching",
                    "suggested_position": "0%",
                    "color": "watch"}

    def _get_top_signal(self, components: dict, stock: dict) -> str:
        best = max(components.items(),
                   key=lambda x: x[1]["points"] / x[1]["max"])
        return best[1]["reasoning_short"]
