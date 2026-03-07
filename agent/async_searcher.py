# agent/async_searcher.py

import os
import asyncio
from tavily import TavilyClient
from dotenv import load_dotenv
from agent.memory import save_to_cache, load_from_cache
import time

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


async def search_web_async(query: str) -> tuple[str, list[dict]]:
    cached = load_from_cache(query)
    if cached:
        print(f"  ⚡ Cache hit:  {query[:45]}")
        return (query, cached)

    try:
        print(f"  🔍 Searching: {query[:45]}")

        response = client.search(
            query=query,
            max_results=5,
            search_depth="basic"
        )

        cleaned = []
        for r in response.get("results", []):
            cleaned.append({
                "title":   r.get("title", ""),
                "link":    r.get("url", ""),
                "snippet": r.get("content", "")
            })

        save_to_cache(query, cleaned)
        return (query, cleaned)

    except Exception as e:
        print(f"  [Search Error] {query[:30]}: {e}")
        return (query, [])


async def search_all_async(queries: list[str]) -> dict:
    start = time.time()
    results = await asyncio.gather(
        *[search_web_async(q) for q in queries]
    )
    elapsed = time.time() - start
    print(f"\n  ⏱️  All searches done in {elapsed:.2f}s")
    return dict(results)


def search_all(queries: list[str]) -> dict:
    return asyncio.run(search_all_async(queries))