# agent/extractor.py

import json
import asyncio
from utils.ai_client import ask_ai, ask_ai_async


# ── Shared prompt templates ───────────────────────────────────────────────────

SYSTEM = """Research extraction expert. JSON only. No markdown. No explanation.
Format exactly:
{"companies":[{"name":"","focus":"","key_fact":"","evidence":{"snippet_ref":1,"source_title":"","source_url":"","confidence":"high"}}],"market_facts":[{"fact":"","evidence":{"snippet_ref":1,"source_title":"","source_url":"","confidence":"high"}}],"challenges":[{"challenge":"","evidence":{"snippet_ref":1,"source_title":"","source_url":"","confidence":"high"}}]}"""


def _build_prompt(snippets: list[dict]) -> str:
    """Build a compact prompt from a small set of snippets."""
    text = ""
    for i, s in enumerate(snippets):
        text += f"[{i+1}] {s['title']} | {s['url']}\n{s['snippet'][:200]}\n\n"
    return f"Extract key facts. Be concise.\n\n{text}\nJSON only:"


def _parse_json(response: str) -> dict:
    """Safely parse JSON — handles all LLM formatting issues."""
    empty = {"companies": [], "market_facts": [], "challenges": []}
    try:
        cleaned = response.strip()
        if "```" in cleaned:
            for part in cleaned.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    cleaned = part
                    break
        start = cleaned.find("{")
        end   = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return empty
        return json.loads(cleaned[start:end])
    except json.JSONDecodeError as e:
        print(f"[Parse Error] {e}")
        return empty


def _merge_extractions(results: list[dict]) -> dict:
    """
    Merge multiple extraction results into one.
    Deduplicate companies by name, facts by text.
    """
    seen_companies = {}
    seen_facts     = set()
    seen_challenges = set()
    merged = {"companies": [], "market_facts": [], "challenges": []}

    for r in results:
        for c in r.get("companies", []):
            name = c.get("name", "")
            if name and name not in seen_companies:
                seen_companies[name] = True
                merged["companies"].append(c)

        for f in r.get("market_facts", []):
            text = f.get("fact", f) if isinstance(f, dict) else f
            if text and text not in seen_facts:
                seen_facts.add(text)
                merged["market_facts"].append(f)

        for c in r.get("challenges", []):
            text = c.get("challenge", c) if isinstance(c, dict) else c
            if text and text not in seen_challenges:
                seen_challenges.add(text)
                merged["challenges"].append(c)

    return merged


# ── Async parallel extraction (FAST) ─────────────────────────────────────────

async def extract_facts_async(search_results: dict) -> dict:
    """
    Parallel extraction — one AI call per search query, all at once.

    BEFORE: 3 queries → 3 sequential AI calls → ~14s
    AFTER:  3 queries → 3 parallel AI calls   →  ~5s
    """

    async def extract_one(query: str, results: list) -> dict:
        """Extract facts from a single query's results."""
        if not results:
            return {"companies": [], "market_facts": [], "challenges": []}

        snippets = [
            {
                "title":   r["title"],
                "snippet": r["snippet"],
                "url":     r["link"]
            }
            for r in results[:2]   # top 2 results per query
        ]

        prompt   = _build_prompt(snippets)
        response = await ask_ai_async(prompt, SYSTEM)
        parsed   = _parse_json(response)
        print(f"  ⚡ Extracted: {query[:40]} → {len(parsed.get('companies',[]))} companies")
        return parsed

    # Fire ALL extractions at the same time!
    tasks   = [extract_one(q, r) for q, r in search_results.items()]
    results = await asyncio.gather(*tasks)

    # Merge all results into one deduplicated set
    merged = _merge_extractions(list(results))
    print(f"  ✅ Total extracted: {len(merged['companies'])} companies, "
          f"{len(merged['market_facts'])} facts, "
          f"{len(merged['challenges'])} challenges")
    return merged


# ── Sync fallback (used by main.py CLI) ───────────────────────────────────────

def extract_facts(search_results: dict) -> dict:
    """
    Sync version for CLI use (main.py).
    FastAPI should use extract_facts_async() instead.
    """
    all_snippets = []
    for query, results in search_results.items():
        for r in results[:2]:
            all_snippets.append({
                "title":   r["title"],
                "snippet": r["snippet"],
                "url":     r["link"]
            })

    prompt   = _build_prompt(all_snippets)
    response = ask_ai(prompt, SYSTEM)
    return _parse_json(response)