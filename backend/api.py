# backend/api.py

import sys
import os
import hashlib
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from agent.planner import plan_research
from agent.async_searcher import search_all_async
from agent.extractor import extract_facts_async
from agent.reporter import generate_report
from agent.memory import get_cache_stats
from agent.memory_store import save_memory, load_memory, get_memory_stats, _merge_memories
from agent.classifier import classify_query          # ← new
from utils.ai_client import ask_ai_async             # ← for quick answers

app = FastAPI(title="AI Research Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str


@app.get("/")
def root():
    return {"status": "AI Research Agent running"}


@app.get("/cache/stats")
def cache_stats():
    return get_cache_stats()


@app.get("/memory/stats")
def memory_stats():
    return get_memory_stats()


@app.get("/observability")
def observability():
    return {"cache": get_cache_stats(), "memory": get_memory_stats()}


# ── Quick Search endpoint ─────────────────────────────────────────────────────

@app.post("/search/quick")
async def quick_search(request: ResearchRequest):
    """
    Quick answer — single AI call, no web search.
    Returns in 3-5 seconds instead of 20-30.
    Best for: definitions, explanations, simple facts.
    """
    query = request.query
    start = time.time()

    system = """You are a knowledgeable AI assistant.
Answer the question clearly and concisely.
Structure your answer with:
- A direct answer (2-3 sentences)
- Key points (3-5 bullet points)
- A one-line summary at the end

Be helpful, accurate, and brief."""

    prompt = f"Answer this question: {query}"

    loop   = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, ask_ai, prompt, system)

    return {
        "query":      query,
        "answer":     answer,
        "mode":       "quick",
        "time_taken": round(time.time() - start, 2),
        "cost":       "$0.0001"
    }


# ── Auto-classify endpoint ────────────────────────────────────────────────────

@app.post("/search/classify")
async def classify(request: ResearchRequest):
    """
    Classifies query as 'quick' or 'research'.
    Frontend uses this to suggest the right mode.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, classify_query, request.query)
    return result


# ── Report cache helpers ──────────────────────────────────────────────────────

def _get_report_cache_path(query: str) -> str:
    key = hashlib.md5(query.lower().strip().encode()).hexdigest()[:10]
    return os.path.join("cache", f"report_{key}.txt")


def _load_cached_report(query: str) -> str | None:
    path = _get_report_cache_path(query)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            print(f"  ⚡ Report cache hit!")
            return f.read()
    return None


def _save_report_cache(query: str, report: str) -> None:
    path = _get_report_cache_path(query)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)


# ── Full Research stream ──────────────────────────────────────────────────────

@app.post("/research/stream")
async def research_stream(request: ResearchRequest):

    async def generate():

        def send(event, data):
            return f"data: {json.dumps({'event': event, 'data': data})}\n\n"

        query     = request.query
        run_start = time.time()
        timings   = {}

        try:
            # ── Phase 1 — Plan ───────────────────────────────────────
            t = time.time()
            yield send("phase", {"phase": 1, "message": "Planning research..."})
            await asyncio.sleep(0.1)
            plan = plan_research(query)
            timings["plan"] = round(time.time() - t, 2)
            yield send("plan", {
                "subtopics": plan["SUBTOPICS"],
                "searches":  plan["SEARCHES"]
            })

            # ── Memory Check ─────────────────────────────────────────
            prior_memory = load_memory(query)
            if prior_memory:
                yield send("memory_hit", {
                    "message":   "Prior knowledge found!",
                    "companies": len(prior_memory.get("companies", []))
                })

            # ── Phase 2 — Search ─────────────────────────────────────
            t = time.time()
            yield send("phase", {"phase": 2, "message": "Searching web..."})
            await asyncio.sleep(0.1)
            results       = await search_all_async(plan["SEARCHES"])
            total_results = sum(len(r) for r in results.values())
            timings["search"] = round(time.time() - t, 2)
            yield send("search_done", {
                "queries": len(results),
                "results": total_results
            })

            # ── Phase 3 — Extract ────────────────────────────────────
            t = time.time()
            yield send("phase", {"phase": 3, "message": "Extracting facts in parallel..."})
            await asyncio.sleep(0.1)
            facts = await extract_facts_async(results)
            timings["extract"] = round(time.time() - t, 2)

            if prior_memory:
                facts = _merge_memories(prior_memory, facts)
                yield send("memory_merged", {
                    "message":         "Merged with prior knowledge",
                    "total_companies": len(facts.get("companies", []))
                })

            yield send("facts", {
                "companies":    facts.get("companies",    []),
                "market_facts": facts.get("market_facts", []),
                "challenges":   facts.get("challenges",   [])
            })

            save_memory(query, facts)

            # ── Phase 4 — Cache + Memory Stats ───────────────────────
            yield send("phase", {"phase": 4, "message": "Saving to memory..."})
            await asyncio.sleep(0.1)
            cache_data  = get_cache_stats()
            memory_data = get_memory_stats()
            yield send("cache", {
                **cache_data,
                "total_topics":    memory_data["total_topics"],
                "total_companies": memory_data["total_companies"]
            })

            # ── Phase 5 — Report ─────────────────────────────────────
            t = time.time()
            yield send("phase", {"phase": 5, "message": "Generating report..."})
            await asyncio.sleep(0.1)

            cached_report = _load_cached_report(query)
            if cached_report:
                report = cached_report
                yield send("report_source", {"source": "cache"})
            else:
                loop   = asyncio.get_event_loop()
                report = await loop.run_in_executor(
                    None, generate_report, query, facts
                )
                _save_report_cache(query, report)
                yield send("report_source", {"source": "generated"})

            timings["report"] = round(time.time() - t, 2)
            yield send("report", {"content": report})

            # ── Done ─────────────────────────────────────────────────
            total_time     = round(time.time() - run_start, 2)
            estimated_cost = round((400 * 3 * 0.00015 + 600 * 3 * 0.0006) / 1000, 4)

            yield send("done", {
                "message":        "Research complete!",
                "timings":        timings,
                "total_time":     total_time,
                "total_searches": len(plan["SEARCHES"]),
                "estimated_cost": estimated_cost,
                "memory_topics":  memory_data["topics"]
            })

        except Exception as e:
            yield send("error", {"message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no"
        }
    )