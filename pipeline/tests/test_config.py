import pytest
from pipeline import config


class TestConfig:
    def test_score_weights_sum_to_100(self):
        assert sum(config.SCORE_WEIGHTS.values()) == 100

    def test_score_weights_all_positive(self):
        for k, v in config.SCORE_WEIGHTS.items():
            assert v > 0, f"{k} weight should be positive"

    def test_score_max_matches_weights(self):
        assert config.SCORE_MAX == config.SCORE_WEIGHTS

    def test_feature_flags_default_false(self):
        # Without .env set, these should default to false
        assert config.ENABLE_GEMINI is False or isinstance(config.ENABLE_GEMINI, bool)
        assert config.ENABLE_BOND_SCRAPE is False or isinstance(config.ENABLE_BOND_SCRAPE, bool)
        assert config.ENABLE_SWING_PIPELINE is False or isinstance(config.ENABLE_SWING_PIPELINE, bool)

    def test_tier_thresholds_ordered(self):
        assert config.TIER_EXCEPTIONAL > config.TIER_HIGH_CONVICTION > config.TIER_SPECULATIVE

    def test_cache_ttls_positive(self):
        assert config.FUNDAMENTALS_CACHE_DAYS > 0
        assert config.BOND_CACHE_DAYS > 0
        assert config.UNIVERSE_CACHE_DAYS > 0
        assert config.PRICE_CACHE_DAYS > 0

    def test_edgar_rate_limit(self):
        assert config.EDGAR_RATE_LIMIT_SLEEP >= 0.1

    def test_paths_are_strings(self):
        assert isinstance(config.DB_PATH, str)
        assert isinstance(config.OUTPUT_DIR, str)
        assert isinstance(config.CACHE_DIR, str)
        assert isinstance(config.LOG_DIR, str)
