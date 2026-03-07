# agent/memory.py

import os
import json
import hashlib
from datetime import datetime, timedelta

# Cache folder
CACHE_DIR = "cache"
CACHE_EXPIRY_HOURS = 24

# Ensure cache folder exists (important for Render / cloud deployments)
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_key(query: str) -> str:
    """
    Convert a query string into a safe filename.
    """
    return hashlib.md5(query.lower().strip().encode()).hexdigest() + ".json"


def save_to_cache(query: str, data: dict) -> None:
    cache_key = _get_cache_key(query)
    cache_path = os.path.join(CACHE_DIR, cache_key)

    cache_data = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2)

    print(f"💾 Cached: {query[:40]}")


def load_from_cache(query: str) -> dict | None:
    cache_key = _get_cache_key(query)
    cache_path = os.path.join(CACHE_DIR, cache_key)

    if not os.path.exists(cache_path):
        return None

    with open(cache_path, "r") as f:
        cache_data = json.load(f)

    saved_time = datetime.fromisoformat(cache_data["timestamp"])
    expiry = saved_time + timedelta(hours=CACHE_EXPIRY_HOURS)

    if datetime.now() > expiry:
        print(f"⏰ Cache expired for: {query[:40]}")
        os.remove(cache_path)
        return None

    print(f"⚡ Cache hit: {query[:40]}")
    return cache_data["data"]


def get_cache_stats() -> dict:
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]

    return {
        "cached_queries": len(files),
        "cache_size_kb": sum(
            os.path.getsize(os.path.join(CACHE_DIR, f))
            for f in files
        ) // 1024
    }