# agent/extractor.py

import asyncio
import json
from utils.ai_client import ask_ai, ask_ai_async


def _clean_json(text: str) -> dict:
    try:
        text  = text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        return json.loads(text[start:end])
    except:
        return {}


def _results_to_text(results: list[dict], max_chars: int = 3000) -> str:
    chunks = []
    total  = 0
    for r in results:
        snippet = r.get("snippet", "")[:200]
        line    = f"- [{r.get('title','')}] {snippet} (source: {r.get('link','')})"
        total  += len(line)
        if total > max_chars:
            break
        chunks.append(line)
    return "\n".join(chunks)


# ── Prompts ───────────────────────────────────────────────────────────────────

MARKET_PROMPT = """Extract market research data from these search results.
Search results:
{results}

Return ONLY valid JSON:
{{
  "companies": [
    {{"name": "...", "focus": "...", "key_fact": "...",
      "evidence": {{"snippet_ref":"...","source_title":"...","source_url":"...","confidence":"high"}}
    }}
  ],
  "market_facts": [
    {{"fact": "...", "evidence": {{"source_title":"...","source_url":"...","confidence":"medium"}}}}
  ],
  "challenges": [
    {{"challenge": "...", "evidence": {{"source_title":"...","source_url":"...","confidence":"low"}}}}
  ]
}}"""

CONCEPT_PROMPT = """Extract a concept explanation from these search results.
Search results:
{results}

Return ONLY valid JSON:
{{
  "definition": "clear 2-3 sentence explanation",
  "how_it_works": ["step 1", "step 2", "step 3"],
  "key_components": [
    {{"name":"...","description":"...",
      "evidence":{{"source_title":"...","source_url":"...","confidence":"high"}}
    }}
  ],
  "use_cases": ["use case 1", "use case 2", "use case 3"],
  "simple_analogy": "real-world analogy",
  "common_misconceptions": ["misconception 1", "misconception 2"]
}}"""

RESEARCH_PROMPT = """Extract academic findings from these search results.
Search results:
{results}

Return ONLY valid JSON:
{{
  "key_findings": [
    {{"finding":"...","evidence":{{"source_title":"...","source_url":"...","confidence":"high"}}}}
  ],
  "methodologies": ["method 1", "method 2"],
  "benchmarks": [
    {{"name":"...","result":"...","evidence":{{"source_title":"...","source_url":"...","confidence":"medium"}}}}
  ],
  "open_problems": ["problem 1", "problem 2"],
  "notable_authors": ["Author 1", "Author 2"]
}}"""

MIXED_PROMPT = """Extract BOTH concept explanation AND company information from these search results.
Search results:
{results}

Return ONLY valid JSON:
{{
  "definition": "clear 2-3 sentence explanation of the concept",
  "how_it_works": ["step 1", "step 2", "step 3"],
  "key_components": [
    {{"name":"...","description":"...",
      "evidence":{{"source_title":"...","source_url":"...","confidence":"high"}}
    }}
  ],
  "use_cases": ["use case 1", "use case 2"],
  "simple_analogy": "real-world analogy",
  "companies": [
    {{"name":"...","focus":"...","key_fact":"...",
      "evidence":{{"snippet_ref":"...","source_title":"...","source_url":"...","confidence":"high"}}
    }}
  ],
  "market_facts": [
    {{"fact":"...","evidence":{{"source_title":"...","source_url":"...","confidence":"medium"}}}}
  ]
}}"""


# ── Single query extraction ───────────────────────────────────────────────────

async def extract_one(query: str, results: list[dict], query_type: str) -> dict:
    results_text = _results_to_text(results)

    if query_type == "concept":
        prompt = CONCEPT_PROMPT.format(results=results_text)
    elif query_type == "research":
        prompt = RESEARCH_PROMPT.format(results=results_text)
    elif query_type == "mixed":
        prompt = MIXED_PROMPT.format(results=results_text)
    else:
        prompt = MARKET_PROMPT.format(results=results_text)

    try:
        response = await ask_ai_async(prompt)
        return _clean_json(response)
    except:
        return {}


# ── Merge helpers ─────────────────────────────────────────────────────────────

def _merge_market(results: list[dict]) -> dict:
    companies    = {}
    market_facts = []
    challenges   = []
    seen         = set()

    for r in results:
        for c in r.get("companies", []):
            name = c.get("name", "").strip()
            if name and name not in companies:
                companies[name] = c
        for f in r.get("market_facts", []):
            t = (f.get("fact") or str(f))[:80]
            if t not in seen: seen.add(t); market_facts.append(f)
        for c in r.get("challenges", []):
            t = (c.get("challenge") or str(c))[:80]
            if t not in seen: seen.add(t); challenges.append(c)

    return {
        "query_type":   "market",
        "companies":    list(companies.values()),
        "market_facts": market_facts,
        "challenges":   challenges,
    }


def _merge_concept(results: list[dict]) -> dict:
    definition     = ""
    how_it_works   = []
    key_components = {}
    use_cases      = []
    analogies      = []
    misconceptions = []
    seen           = set()

    for r in results:
        if not definition and r.get("definition"):
            definition = r["definition"]
        for s in r.get("how_it_works", []):
            if s not in seen: seen.add(s); how_it_works.append(s)
        for c in r.get("key_components", []):
            name = c.get("name", "")
            if name and name not in key_components:
                key_components[name] = c
        for u in r.get("use_cases", []):
            if u not in seen: seen.add(u); use_cases.append(u)
        if r.get("simple_analogy") and not analogies:
            analogies.append(r["simple_analogy"])
        for m in r.get("common_misconceptions", []):
            if m not in seen: seen.add(m); misconceptions.append(m)

    return {
        "query_type":            "concept",
        "definition":            definition,
        "how_it_works":          how_it_works[:6],
        "key_components":        list(key_components.values()),
        "use_cases":             use_cases[:6],
        "simple_analogy":        analogies[0] if analogies else "",
        "common_misconceptions": misconceptions[:4],
    }


def _merge_research(results: list[dict]) -> dict:
    key_findings  = []
    methodologies = []
    benchmarks    = []
    open_problems = []
    authors       = set()
    seen          = set()

    for r in results:
        for f in r.get("key_findings", []):
            t = (f.get("finding") or "")[:80]
            if t and t not in seen: seen.add(t); key_findings.append(f)
        for m in r.get("methodologies", []):
            if m not in seen: seen.add(m); methodologies.append(m)
        for b in r.get("benchmarks", []):
            n = b.get("name", "")
            if n not in seen: seen.add(n); benchmarks.append(b)
        for p in r.get("open_problems", []):
            if p not in seen: seen.add(p); open_problems.append(p)
        for a in r.get("notable_authors", []):
            authors.add(a)

    return {
        "query_type":      "research",
        "key_findings":    key_findings,
        "methodologies":   methodologies[:6],
        "benchmarks":      benchmarks,
        "open_problems":   open_problems[:4],
        "notable_authors": list(authors),
    }


def _merge_mixed(results: list[dict]) -> dict:
    """Merge mixed type — combines concept fields + company fields."""
    # Get concept parts
    concept = _merge_concept(results)
    # Get market parts
    market  = _merge_market(results)

    return {
        "query_type":            "mixed",
        # concept fields
        "definition":            concept["definition"],
        "how_it_works":          concept["how_it_works"],
        "key_components":        concept["key_components"],
        "use_cases":             concept["use_cases"],
        "simple_analogy":        concept["simple_analogy"],
        "common_misconceptions": concept["common_misconceptions"],
        # market fields
        "companies":             market["companies"],
        "market_facts":          market["market_facts"],
    }


# ── Main entry point ──────────────────────────────────────────────────────────

async def extract_facts_async(search_results: dict, query_type: str = "market") -> dict:
    tasks   = [extract_one(q, r, query_type) for q, r in search_results.items()]
    results = await asyncio.gather(*tasks)
    result_list = list(results)

    if query_type == "concept":
        return _merge_concept(result_list)
    elif query_type == "research":
        return _merge_research(result_list)
    elif query_type == "mixed":
        return _merge_mixed(result_list)
    else:
        return _merge_market(result_list)


def extract_facts(search_results: dict, query_type: str = "market") -> dict:
    return asyncio.run(extract_facts_async(search_results, query_type))