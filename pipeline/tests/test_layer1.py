import pytest
import responses
from pipeline.layers.layer1_universe import run


class TestLayer1Universe:
    @responses.activate
    def test_fetches_and_filters_us_exchanges(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.config.CACHE_DIR", str(tmp_path / "cache"))
        responses.add(
            responses.GET,
            "https://www.sec.gov/files/company_tickers_exchange.json",
            json={
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [
                    [1326380, "GameStop Corp", "GME", "NYSE"],
                    [320193, "Apple Inc", "AAPL", "Nasdaq"],
                    [999999, "Foreign Corp", "FRGN", "London"],
                ]
            },
            status=200,
        )
        result = run({}, {})
        tickers = [t["ticker"] for t in result]
        assert "GME" in tickers
        assert "AAPL" in tickers
        assert "FRGN" not in tickers  # filtered: not US exchange

    @responses.activate
    def test_validates_response_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.config.CACHE_DIR", str(tmp_path / "cache"))
        responses.add(
            responses.GET,
            "https://www.sec.gov/files/company_tickers_exchange.json",
            json={"data": [{"wrong": "format"}]},
            status=200,
        )
        result = run({}, {})
        assert result == []

    @responses.activate
    def test_empty_data_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.config.CACHE_DIR", str(tmp_path / "cache"))
        responses.add(
            responses.GET,
            "https://www.sec.gov/files/company_tickers_exchange.json",
            json={"data": []},
            status=200,
        )
        result = run({}, {})
        assert result == []

    @responses.activate
    def test_cik_is_zero_padded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.config.CACHE_DIR", str(tmp_path / "cache"))
        responses.add(
            responses.GET,
            "https://www.sec.gov/files/company_tickers_exchange.json",
            json={
                "data": [[1326380, "GameStop Corp", "GME", "NYSE"]]
            },
            status=200,
        )
        result = run({}, {})
        assert result[0]["cik"] == "0001326380"
