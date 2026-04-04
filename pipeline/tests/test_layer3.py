import pytest
from pipeline.layers._fundamentals_parser import FundamentalsParser


class TestFundamentalsParser:
    def _make_facts(self, concepts):
        """Helper to build EDGAR facts structure."""
        us_gaap = {}
        for tag, entries in concepts.items():
            us_gaap[tag] = {"units": {"USD": entries}}
        return {"facts": {"us-gaap": us_gaap}}

    def test_annual_series_excludes_q1_q2_q3(self):
        """XBRL fix: Q1/Q2/Q3 frames must be excluded from annual data."""
        facts = self._make_facts({
            "Revenues": [
                {"form": "10-K", "frame": "CY2023", "val": 1000, "end": "2023-12-31"},
                {"form": "10-Q", "frame": "CY2023Q1", "val": 250, "end": "2023-03-31"},
                {"form": "10-Q", "frame": "CY2023Q2", "val": 500, "end": "2023-06-30"},
                {"form": "10-Q", "frame": "CY2023Q3", "val": 750, "end": "2023-09-30"},
            ]
        })
        parser = FundamentalsParser(facts, "TEST")
        series = parser.get_annual_series("Revenues")
        assert 2023 in series
        assert series[2023] == 1000
        # Should only have the annual entry
        assert len(series) == 1

    def test_annual_series_allows_q4i(self):
        """CY2023Q4I should be treated as annual (full year)."""
        facts = self._make_facts({
            "Revenues": [
                {"form": "10-K", "frame": "CY2023Q4I", "val": 1000, "end": "2023-12-31"},
            ]
        })
        parser = FundamentalsParser(facts, "TEST")
        series = parser.get_annual_series("Revenues")
        assert 2023 in series
        assert series[2023] == 1000

    def test_get_latest_annual(self):
        facts = self._make_facts({
            "Assets": [
                {"form": "10-K", "frame": "CY2022", "val": 500, "end": "2022-12-31"},
                {"form": "10-K", "frame": "CY2023", "val": 600, "end": "2023-12-31"},
            ]
        })
        parser = FundamentalsParser(facts, "TEST")
        latest = parser.get_latest_annual("Assets")
        assert latest == 600

    def test_fallback_tags(self):
        facts = self._make_facts({
            "SalesRevenueNet": [
                {"form": "10-K", "frame": "CY2023", "val": 900, "end": "2023-12-31"},
            ]
        })
        parser = FundamentalsParser(facts, "TEST")
        rev = parser.get_latest_annual("Revenues", fallbacks=["SalesRevenueNet"])
        assert rev == 900

    def test_missing_tag_returns_none(self):
        facts = {"facts": {"us-gaap": {}}}
        parser = FundamentalsParser(facts, "TEST")
        assert parser.get_latest_annual("NonExistentTag") is None

    def test_get_latest_returns_most_recent(self):
        facts = self._make_facts({
            "CommonStockSharesOutstanding": [
                {"form": "10-Q", "frame": "CY2023Q1", "val": 100, "end": "2023-03-31"},
                {"form": "10-K", "frame": "CY2023", "val": 200, "end": "2023-12-31"},
            ]
        })
        # Override to use shares unit
        facts["facts"]["us-gaap"]["CommonStockSharesOutstanding"]["units"] = {
            "shares": [
                {"form": "10-Q", "frame": "CY2023Q1", "val": 100, "end": "2023-03-31"},
                {"form": "10-K", "frame": "CY2023", "val": 200, "end": "2023-12-31"},
            ]
        }
        parser = FundamentalsParser(facts, "TEST")
        latest = parser.get_latest("CommonStockSharesOutstanding")
        assert latest == 200  # most recent by end date
