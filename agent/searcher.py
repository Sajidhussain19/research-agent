# agent/searcher.py

import os
from tavily import TavilyClient
from dotenv import load_dotenv
from agent.memory import save_to_cache, load_from_cache

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def search_web(query: str) -> list[dict]:
    """
    Search the web — but check cache first!
    Cache hit  = instant result, zero API cost
    Cache miss = real search, then save to cache
    """

    # 1. Check cache first
    cached = load_from_cache(query)
    if cached:
        return cached          # return instantly! ⚡

    # 2. Cache miss — do real search
    try:
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

        # 3. Save to cache for next time
        save_to_cache(query, cleaned)
        return cleaned

    except Exception as e:
        print(f"[Search Error] {e}")
        return []


def search_all(queries: list[str]) -> dict:
    all_results = {}
    for query in queries:
        print(f"  🔍 Searching: {query}")
        results = search_web(query)
        all_results[query] = results
        print(f"     ✅ Found {len(results)} results")
    return all_results