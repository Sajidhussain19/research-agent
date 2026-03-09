import os
from datetime import datetime
from utils.ai_client import ask_ai

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def _generate_section(title: str, query: str, context: str):

    system = "You are a professional research analyst."

    prompt = f"""
Write the section: {title}

Topic: {query}

Use the following research data:

{context}

Write clearly and professionally.
Limit to 120 words.
"""

    return ask_ai(prompt, system)


def generate_report(query: str, facts: dict):

    companies = "\n".join([
        f"- {c['name']}: {c.get('focus','')} {c.get('key_fact','')}"
        for c in facts.get("companies", [])
    ])

    market = "\n".join([
        f"- {f.get('fact', f) if isinstance(f, dict) else f}"
        for f in facts.get("market_facts", [])
    ])

    challenges = "\n".join([
        f"- {c.get('challenge', c) if isinstance(c, dict) else c}"
        for c in facts.get("challenges", [])
    ])

    context = f"""
COMPANIES:
{companies}

MARKET:
{market}

CHALLENGES:
{challenges}
"""

    summary = _generate_section("Executive Summary", query, context)
    intro = _generate_section("Introduction", query, context)
    companies_sec = _generate_section("Key Companies", query, companies)
    market_sec = _generate_section("Market Overview", query, market)
    challenges_sec = _generate_section("Challenges", query, challenges)
    conclusion = _generate_section("Conclusion", query, context)

    report = f"""
# {query.title()}

## Executive Summary
{summary}

## Introduction
{intro}

## Key Companies
{companies_sec}

## Market Overview
{market_sec}

## Challenges
{challenges_sec}

## Conclusion
{conclusion}

## Sources
- Tavily Web Search · {datetime.now().strftime("%Y-%m-%d")}
"""

    _save_report(query, report)

    return report


def _save_report(query: str, report: str):

    safe_name = "".join(c if c.isalnum() else "_" for c in query.lower())[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filepath = os.path.join(REPORTS_DIR, f"{safe_name}_{timestamp}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"💾 Report saved: {filepath}")