# agent/async_searcher.py

import os
import asyncio
import time
from tavily import TavilyClient
from dotenv import load_dotenv
from agent.memory import save_to_cache, load_from_cache

load_dotenv()

# Sync client wrapped in executor — works with ALL tavily versions
_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _search_sync(query: str) -> list[dict]:
    """Blocking search — runs in thread pool so it doesn't block asyncio."""
    response = _client.search(
        query=query,
        max_results=5,
        search_depth="advanced",  # fresher results
        days=90                   # last 90 days only
    )
    return [
        {
            "title":   r.get("title",   ""),
            "link":    r.get("url",     ""),
            "snippet": r.get("content", "")
        }
        for r in response.get("results", [])
    ]


async def search_web_async(query: str) -> tuple[str, list[dict]]:
    # Check cache first
    cached = load_from_cache(query)
    if cached:
        print(f"  ⚡ Cache hit:  {query[:45]}")
        return (query, cached)

    try:
        print(f"  🔍 Searching: {query[:45]}")

        # Run blocking search in thread pool — keeps asyncio non-blocking
        loop    = asyncio.get_event_loop()
        cleaned = await loop.run_in_executor(None, _search_sync, query)

        save_to_cache(query, cleaned)
        return (query, cleaned)

    except Exception as e:
        print(f"  [Search Error] {query[:30]}: {e}")
        return (query, [])


async def search_all_async(queries: list[str]) -> dict:
    start   = time.time()
    results = await asyncio.gather(*[search_web_async(q) for q in queries])
    print(f"\n  ⏱️  All searches done in {time.time()-start:.2f}s")
    return dict(results)


def search_all(queries: list[str]) -> dict:
    """Sync version for CLI use (main.py)."""
    return asyncio.run(search_all_async(queries))