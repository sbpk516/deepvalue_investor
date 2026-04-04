"""
Helper class for parsing SEC EDGAR XBRL company facts.
Handles tag synonyms and missing data gracefully.
"""
from __future__ import annotations


class FundamentalsParser:
    def __init__(self, facts: dict, ticker: str):
        self.facts = facts
        self.ticker = ticker
        self.us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def _get_concept(self, tag: str) -> dict | None:
        return self.us_gaap.get(tag)

    def get_annual_series(self, tag: str,
                          fallbacks: list[str] = None) -> dict:
        """Return {year: value} dict for annual data."""
        tags_to_try = [tag] + (fallbacks or [])
        for t in tags_to_try:
            concept = self._get_concept(t)
            if not concept:
                continue
            units = concept.get("units", {})
            # Try USD then shares
            for unit_key in ("USD", "shares"):
                if unit_key not in units:
                    continue
                entries = [
                    e for e in units[unit_key]
                    if e.get("form") in ("10-K", "10-K/A")
                    and e.get("frame", "").startswith("CY")
                    # FIX: original len==6 only matched CY2023 format.
                    # EDGAR also uses CY2023Q4I for many annual filings.
                    # Correct approach: exclude Q1/Q2/Q3 quarterly frames,
                    # but allow CY2023 (annual) and CY2023Q4I (full year).
                    and not any(
                        e.get("frame", "").endswith(s)
                        for s in ("Q1", "Q2", "Q3", "Q1I", "Q2I", "Q3I")
                    )
                ]
                if entries:
                    result = {}
                    for e in entries:
                        # Extract year from frame: CY2023 -> 2023, CY2023Q4I -> 2023
                        frame = e["frame"][2:]  # strip "CY"
                        year_str = frame[:4]    # first 4 chars are always the year
                        try:
                            result[int(year_str)] = e["val"]
                        except ValueError:
                            continue
                    return result
        return {}

    def get_latest_annual(self, tag: str,
                          fallbacks: list[str] = None) -> float | None:
        series = self.get_annual_series(tag, fallbacks)
        if not series:
            return None
        latest_year = max(series.keys())
        return series[latest_year]

    def get_latest(self, tag: str,
                   fallbacks: list[str] = None) -> float | None:
        """Get most recent value regardless of period type."""
        tags_to_try = [tag] + (fallbacks or [])
        for t in tags_to_try:
            concept = self._get_concept(t)
            if not concept:
                continue
            for unit_key in ("USD", "shares", "pure"):
                entries = concept.get("units", {}).get(unit_key, [])
                if entries:
                    latest = max(entries, key=lambda x: x.get("end", ""))
                    return latest.get("val")
        return None
