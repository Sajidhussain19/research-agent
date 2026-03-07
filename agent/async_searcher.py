# agent/async_searcher.py

import os
import asyncio
import time
from tavily import AsyncTavilyClient          # ← async client (not TavilyClient)
from dotenv import load_dotenv
from agent.memory import save_to_cache, load_from_cache

load_dotenv()

# AsyncTavilyClient — non-blocking, works properly inside asyncio.gather()
client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


async def search_web_async(query: str) -> tuple[str, list[dict]]:
    cached = load_from_cache(query)
    if cached:
        print(f"  ⚡ Cache hit:  {query[:45]}")
        return (query, cached)

    try:
        print(f"  🔍 Searching: {query[:45]}")

        # await — properly non-blocking now
        # advanced depth + days=90 → recent results only!
        response = await client.search(
            query=query,
            max_results=5,
            search_depth="advanced",  # fresher, more relevant
            days=90                   # only last 90 days
        )

        cleaned = [
            {
                "title":   r.get("title",   ""),
                "link":    r.get("url",     ""),
                "snippet": r.get("content", "")
            }
            for r in response.get("results", [])
        ]

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