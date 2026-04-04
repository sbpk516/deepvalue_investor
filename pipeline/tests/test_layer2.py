import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from pipeline.layers.layer2_price import _evaluate_ticker


class TestLayer2Price:
    def _make_series(self, prices):
        """Create a weekly close series."""
        dates = pd.date_range(end="2026-04-03", periods=len(prices), freq="W")
        df = pd.DataFrame({"Close": prices}, index=dates)
        return df

    def test_down_60pct_passes(self):
        """Stock down 60% from 3yr high should pass."""
        prices = [100.0] * 100 + [40.0] * 56  # high=100, current=40, down 60%
        df = self._make_series(prices)
        result = _evaluate_ticker("TEST", df, {"ticker": "TEST"})
        assert result is not None
        assert result["pct_below_3yr_high"] <= -0.40

    def test_down_10pct_filtered(self):
        """Stock only down 10% should be filtered out."""
        prices = [100.0] * 100 + [90.0] * 56
        df = self._make_series(prices)
        result = _evaluate_ticker("TEST", df, {"ticker": "TEST"})
        assert result is None

    def test_empty_dataframe_filtered(self):
        result = _evaluate_ticker("TEST", pd.DataFrame(), {"ticker": "TEST"})
        assert result is None

    def test_too_few_weeks_filtered(self):
        prices = [10.0] * 20  # less than 52 weeks
        df = self._make_series(prices)
        result = _evaluate_ticker("TEST", df, {"ticker": "TEST"})
        assert result is None

    def test_price_series_attached(self):
        """_price_series should be attached for Layer 6 RSI reuse."""
        prices = [100.0] * 100 + [40.0] * 56
        df = self._make_series(prices)
        result = _evaluate_ticker("TEST", df, {"ticker": "TEST"})
        assert result is not None
        assert "_price_series" in result

    def test_aapl_should_not_pass(self):
        """AAPL-like stock (slightly below high) should be filtered."""
        prices = [180.0] * 100 + [170.0] * 56  # only ~6% below high
        df = self._make_series(prices)
        result = _evaluate_ticker("AAPL", df, {"ticker": "AAPL"})
        assert result is None
