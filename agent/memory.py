# agent/memory.py

import os
import json
import hashlib
from datetime import datetime, timedelta

# Cache folder — already created in Phase 1
CACHE_DIR = "cache"
CACHE_EXPIRY_HOURS = 24  # cached results expire after 24 hours

def _get_cache_key(query: str) -> str:
    """
    Convert a query string into a safe filename.
    
    "AI startups India" → "a3f5bc92.json"
    
    We use hashing so special characters don't break filenames.
    This is called a 'cache key' — a unique ID for each query.
    """
    return hashlib.md5(query.lower().strip().encode()).hexdigest() + ".json"


def save_to_cache(query: str, data: dict) -> None:
    """
    Save search results to a JSON file in cache/
    Also saves timestamp so we know when it expires.
    """
    cache_key  = _get_cache_key(query)
    cache_path = os.path.join(CACHE_DIR, cache_key)

    # Wrap data with metadata
    cache_data = {
        "query":      query,
        "timestamp":  datetime.now().isoformat(),
        "data":       data
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2)

    print(f"  💾 Cached: {query[:40]}")


def load_from_cache(query: str) -> dict | None:
    """
    Try to load cached results for a query.
    Returns None if:
    - cache doesn't exist
    - cache is expired (older than 24 hours)
    """
    cache_key  = _get_cache_key(query)
    cache_path = os.path.join(CACHE_DIR, cache_key)

    # Check if cache file exists
    if not os.path.exists(cache_path):
        return None

    with open(cache_path, "r") as f:
        cache_data = json.load(f)

    # Check if cache is expired
    saved_time = datetime.fromisoformat(cache_data["timestamp"])
    expiry     = saved_time + timedelta(hours=CACHE_EXPIRY_HOURS)

    if datetime.now() > expiry:
        print(f"  ⏰ Cache expired for: {query[:40]}")
        os.remove(cache_path)   # delete old cache
        return None

    print(f"  ⚡ Cache hit: {query[:40]}")
    return cache_data["data"]


def get_cache_stats() -> dict:
    """
    Show how many queries are cached and how much
    space we're saving.
    Useful for observability — knowing what's happening
    inside your agent.
    """
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    return {
        "cached_queries": len(files),
        "cache_size_kb":  sum(
            os.path.getsize(os.path.join(CACHE_DIR, f))
            for f in files
        ) // 1024
    }