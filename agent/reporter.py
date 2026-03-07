# agent/reporter.py

import os
from datetime import datetime
from utils.ai_client import ask_ai

REPORTS_DIR = "reports"

def generate_report(query: str, facts: dict) -> str:
    """
    Generates a professional report using AI.
    Optimized: concise prompt = faster response.
    """

    # Build compact context
    companies_text = ""
    for c in facts.get("companies", []):
        companies_text += f"- {c['name']}: {c.get('focus','')}. {c.get('key_fact','')}\n"

    market_text = "\n".join([
        f"- {f.get('fact', f) if isinstance(f, dict) else f}"
        for f in facts.get("market_facts", [])
    ])

    challenges_text = "\n".join([
        f"- {c.get('challenge', c) if isinstance(c, dict) else c}"
        for c in facts.get("challenges", [])
    ])

    system = "Professional research analyst. Write clear, concise reports. Use only provided data."

    # Shorter, more direct prompt = faster AI response
    prompt = f"""Write a concise research report on: "{query}"

Use EXACTLY these headers:
# {query.title()}
## Executive Summary
## Key Companies
## Market Overview
## Challenges
## Conclusion
## Sources
- Tavily Web Search · {datetime.now().strftime("%Y-%m-%d")}

Data:
COMPANIES:
{companies_text}
MARKET FACTS:
{market_text}
CHALLENGES:
{challenges_text}

Keep it under 350 words. Be direct and insightful."""

    report = ask_ai(prompt, system)
    _save_report(query, report)
    return report


def _save_report(query: str, report: str) -> None:
    """Save report to disk with timestamp."""
    safe_name  = "".join(c if c.isalnum() else "_" for c in query.lower())[:50]
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath   = os.path.join(REPORTS_DIR, f"{safe_name}_{timestamp}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Research Query: {query}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(report)

    print(f"\n  💾 Report saved: {filepath}")