# agent/planner.py

from utils.ai_client import ask_ai
import datetime


def plan_research(query: str) -> dict:
    current_year = datetime.datetime.now().year

    system = f"""You are a research planning expert.

Today's year is {current_year}. Always use {current_year} in ALL search queries.

Detect QUERY_TYPE:
  concept  = definitions, explanations, "what is", "how does"
  market   = companies, startups, industry, funding, market trends
  research = academic papers, benchmarks, surveys
  mixed    = both concept/explanation AND companies/usage

ALWAYS respond in this EXACT format:

QUERY_TYPE: concept
SUBTOPICS: topic1, topic2, topic3
SEARCHES: search query {current_year} | search query {current_year} | search query {current_year}
REPORT_TYPE: concept_explanation
"""

    prompt = f"""Classify and plan research for the following query:

"{query}"

Use {current_year} in every search query.
"""

    response = ask_ai(prompt, system)

    # --------------------------------------------------
    # Parse AI response
    # --------------------------------------------------

    plan = {}

    for line in response.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            plan[key.strip()] = value.strip()

    plan["SUBTOPICS"] = [
        s.strip() for s in plan.get("SUBTOPICS", "").split(",") if s.strip()
    ]

    plan["SEARCHES"] = [
        s.strip() for s in plan.get("SEARCHES", "").split("|") if s.strip()
    ]

    plan["QUERY_TYPE"] = plan.get("QUERY_TYPE", "market").lower().strip()

    # --------------------------------------------------
    # Rule-based query detection (more reliable than LLM)
    # --------------------------------------------------

    q = query.lower().strip()

    # Concept triggers
    concept_triggers = [
        "what is",
        "what are",
        "how does",
        "how do",
        "explain",
        "definition",
        "meaning",
        "understand",
        "working of",
    ]

    # Research triggers
    research_triggers = [
        "latest",
        "recent",
        "state of the art",
        "sota",
        "benchmark",
        "survey",
        "paper",
        "research",
    ]

    # Market keywords
    market_keywords = [
        "company",
        "companies",
        "startup",
        "startups",
        "industry",
        "market",
        "firms",
    ]

    market_modifiers = [
        "top",
        "best",
        "leading",
        "biggest",
        "in india",
        "using",
        "working on",
    ]

    # Detection
    has_concept = any(t in q for t in concept_triggers)
    has_research = any(t in q for t in research_triggers)

    has_market = (
        any(k in q for k in market_keywords)
        or (
            any(m in q for m in market_modifiers)
            and ("company" in q or "companies" in q)
        )
    )

    # Extra rule: detect combined queries
    if " and " in q and ("company" in q or "companies" in q):
        has_market = True
        has_concept = True

    # --------------------------------------------------
    # Final classification override
    # --------------------------------------------------

    if has_concept and has_market:
        plan["QUERY_TYPE"] = "mixed"

    elif has_concept:
        plan["QUERY_TYPE"] = "concept"

    elif has_research:
        plan["QUERY_TYPE"] = "research"

    elif has_market:
        plan["QUERY_TYPE"] = "market"

    # --------------------------------------------------
    # Debug logs
    # --------------------------------------------------

    print(f"\n🧠 Query analysis:")
    print(f"   Concept detected : {has_concept}")
    print(f"   Market detected  : {has_market}")
    print(f"   Research detected: {has_research}")
    print(f"   Final type       : {plan['QUERY_TYPE']}")
    print(f"   Query            : {query[:60]}\n")

    return plan