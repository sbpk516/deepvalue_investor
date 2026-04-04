import pytest
import os
import time
import json
from unittest.mock import patch
from pipeline.utils.cache import cache_get, cache_set, cache_get_pickle, cache_set_pickle


class TestCache:
    def test_cache_miss_returns_none(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            result = cache_get("test", "nonexistent", ttl_days=1)
            assert result is None

    def test_cache_hit(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            cache_set("test", "key1", {"value": 42})
            result = cache_get("test", "key1", ttl_days=1)
            assert result == {"value": 42}

    def test_cache_expired(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            cache_set("test", "key1", {"value": 42})
            # Set file mtime to 2 days ago
            path = os.path.join(tmp_cache, "test", "key1.json")
            old_time = time.time() - 2 * 86400
            os.utime(path, (old_time, old_time))
            result = cache_get("test", "key1", ttl_days=1)
            assert result is None

    def test_json_roundtrip(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            data = {"string": "hello", "number": 42, "list": [1, 2, 3]}
            cache_set("test", "key1", data)
            result = cache_get("test", "key1", ttl_days=1)
            assert result == data

    def test_pickle_roundtrip(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            data = {"tuple": (1, 2), "set": {3, 4}}
            cache_set_pickle("test", "key1", data)
            result = cache_get_pickle("test", "key1", ttl_days=1)
            assert result == data

    def test_pickle_miss(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            result = cache_get_pickle("test", "nonexistent", ttl_days=1)
            assert result is None

    def test_cache_key_sanitization(self, tmp_cache):
        with patch("pipeline.config.CACHE_DIR", tmp_cache):
            cache_set("test", "path/with:special\\chars", {"ok": True})
            result = cache_get("test", "path/with:special\\chars", ttl_days=1)
            assert result == {"ok": True}
