import pytest
from pipeline.scoring.confidence_score import RKScorer
from pipeline.scoring.upside_calc import UpsideCalc
from pipeline.scoring.risk_flags import RiskFlagGenerator
from pipeline.scoring.action_steps import ActionStepGenerator


class TestRKScorer:
    def _make_stock(self, **overrides):
        base = {
            "ticker": "TEST", "price": 10.0, "cik": "0001234567",
            "insider_buy_amount": 500000, "insider_is_ceo_cfo": True,
            "insider_is_10b51_plan": False, "insider_buy_count": 1,
            "insider_buy_role": "CEO", "insider_buy_name": "John Doe",
            "insider_buy_date": "2026-01-15",
            "bond_tier": "unavailable", "net_overhang_fcf_ratio": 3,
            "fcf_yield": 0.15, "price_to_tbv": 0.8,
            "value_fund_name": "Baupost Group", "value_fund_pct": 0.06,
            "insider_ownership_pct": 0.15,
            "rsi_weekly": 32, "rsi_trend": "improving",
            "weeks_rsi_improving": 4, "support_retest": False,
            "sector_context_modifier": 0,
            "shares_outstanding": 1000000, "fcf_3yr_avg": 5000000,
            "fcf_series": {2021: 4000000, 2022: 5000000, 2023: 6000000},
        }
        base.update(overrides)
        return base

    def test_score_range(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        assert 0 <= result["score_total"] <= 100

    def test_good_stock_scores_high(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        assert result["score_total"] >= 60

    def test_aapl_scores_low(self):
        scorer = RKScorer()
        stock = self._make_stock(
            ticker="AAPL", insider_buy_amount=0,
            bond_tier="unavailable", net_overhang_fcf_ratio=1,
            fcf_yield=0.03, price_to_tbv=5.0,
            value_fund_name=None, value_fund_pct=0,
            insider_ownership_pct=0.01,
            rsi_weekly=55, rsi_trend="declining",
        )
        result = scorer.score(stock)
        assert result["score_total"] < 35

    def test_component_caps_enforced(self):
        scorer = RKScorer()
        stock = self._make_stock(insider_buy_amount=10_000_000)
        result = scorer.score(stock)
        for name, comp in result["components"].items():
            assert comp["points"] <= comp["max"], \
                f"{name}: {comp['points']} > max {comp['max']}"

    def test_10b51_halves_insider_score(self):
        scorer = RKScorer()
        normal = self._make_stock()
        result_normal = scorer.score(normal)

        plan = self._make_stock(insider_is_10b51_plan=True)
        result_plan = scorer.score(plan)

        assert (result_plan["components"]["insider"]["points"] <
                result_normal["components"]["insider"]["points"])

    def test_stale_bonds_reduce_score(self):
        scorer = RKScorer()
        fresh = self._make_stock(bond_tier="safe", bond_price=95, bond_is_stale=False)
        stale = self._make_stock(bond_tier="safe", bond_price=95, bond_is_stale=True)
        result_fresh = scorer.score(fresh)
        result_stale = scorer.score(stale)
        assert (result_stale["components"]["bonds"]["points"] <
                result_fresh["components"]["bonds"]["points"])

    def test_tier_labels(self):
        scorer = RKScorer()
        assert scorer._get_tier(85)["label"] == "Exceptional"
        assert scorer._get_tier(70)["label"] == "High Conviction"
        assert scorer._get_tier(50)["label"] == "Speculative"
        assert scorer._get_tier(30)["label"] == "Watch Only"

    def test_transparency_has_all_components(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        assert "transparency" in result
        t = result["transparency"]
        assert "summary" in t
        assert "total_explanation" in t
        assert "components" in t
        for name in ("insider", "bonds", "fcf", "institutional", "technical"):
            assert name in t["components"]

    def test_weights_sum_to_100(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        max_sum = sum(c["max"] for c in result["components"].values())
        assert max_sum == 100

    def test_risk_flags_generated(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        assert isinstance(result["risk_flags"], list)

    def test_action_steps_generated(self):
        scorer = RKScorer()
        stock = self._make_stock()
        result = scorer.score(stock)
        assert isinstance(result["action_steps"], list)
        assert len(result["action_steps"]) >= 1


class TestUpsideCalc:
    def test_upside_with_fcf(self):
        calc = UpsideCalc()
        result = calc.calculate({
            "price": 10.0, "shares_outstanding": 1000000,
            "fcf_3yr_avg": 5000000, "diluted_shares": 1000000,
            "fcf_series": {2021: 4000000, 2022: 5000000, 2023: 6000000},
        })
        assert result["conservative"] is not None
        assert result["bull"] is not None
        assert result["conservative"] > 0

    def test_upside_no_price(self):
        calc = UpsideCalc()
        result = calc.calculate({"price": 0})
        assert result["conservative"] is None


class TestRiskFlags:
    def test_no_value_fund_flag(self):
        gen = RiskFlagGenerator()
        flags = gen.generate({"value_fund_name": None}, {})
        keys = [f["key"] for f in flags]
        assert "no_value_fund" in keys

    def test_secular_decline_flag(self):
        gen = RiskFlagGenerator()
        flags = gen.generate({"decline_type": "secular"}, {})
        keys = [f["key"] for f in flags]
        assert "secular_decline" in keys
