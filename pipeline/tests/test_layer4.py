import pytest
from unittest.mock import patch, MagicMock
from pipeline.scrapers.openinsider import _parse_row, PRIORITY_ROLES
from pipeline.scrapers.finra_trace import assign_bond_tier


class TestOpenInsiderParser:
    def test_ceo_buy_parsed(self):
        row = MagicMock()
        row.get = lambda k, d="": {
            "Title": "CEO", "Value": "$500,000",
            "Ticker": "GME", "Insider Name": "John Doe",
            "Trade\xa0Date": "2026-01-15",
        }.get(k, d)
        row.values = lambda: ["GME", "2026-01-15", "", "John Doe", "CEO",
                               "", "", "", "", "$500,000", "", "", ""]
        result = _parse_row(row)
        assert result is not None
        assert result["role_score"] == 30
        assert result["value"] == 500000
        assert result["is_ceo_cfo_chairman"] is True

    def test_small_buy_filtered(self):
        row = MagicMock()
        row.get = lambda k, d="": {
            "Title": "Director", "Value": "$5,000",
            "Ticker": "GME", "Insider Name": "Jane",
            "Trade\xa0Date": "2026-01-15",
        }.get(k, d)
        row.values = lambda: ["GME", "2026-01-15", "", "Jane", "Director",
                               "", "", "", "", "$5,000", "", "", ""]
        result = _parse_row(row)
        assert result is None  # below $10k threshold

    def test_10b51_plan_detected(self):
        row = MagicMock()
        row.get = lambda k, d="": {
            "Title": "CEO", "Value": "$300,000",
            "Ticker": "GME", "Insider Name": "John",
            "Trade\xa0Date": "2026-01-15",
        }.get(k, d)
        row.values = lambda: ["GME", "2026-01-15", "", "John", "CEO",
                               "", "", "", "", "$300,000", "",
                               "Rule 10b5-1 plan", ""]
        result = _parse_row(row)
        assert result is not None
        assert result["is_10b51_plan"] is True

    def test_irrelevant_role_filtered(self):
        row = MagicMock()
        row.get = lambda k, d="": {
            "Title": "Secretary", "Value": "$100,000",
        }.get(k, d)
        row.values = lambda: []
        result = _parse_row(row)
        assert result is None


class TestBondTierAssignment:
    def test_safe(self):
        assert assign_bond_tier(95) == "safe"

    def test_caution(self):
        assert assign_bond_tier(85) == "caution"

    def test_elevated(self):
        assert assign_bond_tier(75) == "elevated"

    def test_high_risk(self):
        assert assign_bond_tier(55) == "high_risk"

    def test_critical(self):
        assert assign_bond_tier(30) == "critical"

    def test_unavailable(self):
        assert assign_bond_tier(None) == "unavailable"

    def test_boundary_safe(self):
        assert assign_bond_tier(90) == "safe"

    def test_stale_bond_flag(self):
        """Bond staleness should be tracked."""
        from pipeline.scrapers.finra_trace import _parse_finra_api_response
        item = {
            "lastSalePrice": 85,
            "lastSaleDate": "2020-01-01",  # very old
            "totalVolume": 2,
        }
        result = _parse_finra_api_response(item)
        assert result["is_stale"] is True
