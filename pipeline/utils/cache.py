from __future__ import annotations

import os
import json
import pickle
from datetime import datetime, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def _cache_path(category: str, key: str, ext: str = "json") -> str:
    folder = os.path.join(config.CACHE_DIR, category)
    os.makedirs(folder, exist_ok=True)
    # Sanitise key for use as filename
    safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
    return os.path.join(folder, f"{safe_key}.{ext}")

def cache_get(category: str, key: str, ttl_days: int) -> dict | None:
    """Return cached data if fresh, else None."""
    path = _cache_path(category, key)
    if not os.path.exists(path):
        return None
    age_days = (datetime.now().timestamp() - os.path.getmtime(path)) / 86400
    if age_days > ttl_days:
        logger.debug(f"Cache stale ({age_days:.1f}d > {ttl_days}d): {category}/{key}")
        return None
    with open(path) as f:
        return json.load(f)

def cache_set(category: str, key: str, data: dict) -> None:
    """Write data to cache."""
    path = _cache_path(category, key)
    with open(path, "w") as f:
        json.dump(data, f, default=str)

def cache_get_pickle(category: str, key: str, ttl_days: int):
    """For non-JSON data (e.g. pandas DataFrames)."""
    path = _cache_path(category, key, ext="pkl")
    if not os.path.exists(path):
        return None
    age_days = (datetime.now().timestamp() - os.path.getmtime(path)) / 86400
    if age_days > ttl_days:
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def cache_set_pickle(category: str, key: str, data) -> None:
    path = _cache_path(category, key, ext="pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)
