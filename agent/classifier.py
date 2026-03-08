# agent/classifier.py
# Decides: is this a quick question or deep research?
# This is "intent classification" — a core AI/ML concept

import json
from utils.ai_client import ask_ai


def classify_query(query: str) -> dict:
    """
    Classifies a query as 'quick' or 'research'.

    quick    = facts, definitions, explanations, how-to, simple questions
    research = market analysis, startup landscape, trends,
               competitive analysis, industry reports, company comparisons
    """

    system = """You are a query classifier. Respond with ONLY a JSON object, nothing else.

quick   = simple facts, definitions, explanations, how-to, general knowledge
research = market analysis, startup landscape, trends, competitive analysis,
           industry reports, "top companies", "best startups", investment analysis

Examples:
"What is machine learning?" → {"type":"quick","reason":"simple definition"}
"AI startups in India 2026" → {"type":"research","reason":"needs web search and market analysis"}
"How does GPT work?"        → {"type":"quick","reason":"explanation question"}
"Top fintech companies 2026"→ {"type":"research","reason":"needs current market data"}"""

    prompt = f'Classify this query: "{query}"'

    try:
        response = ask_ai(prompt, system)
        cleaned  = response.strip()
        start    = cleaned.find("{")
        end      = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return {"type": "research", "reason": "could not classify"}
        return json.loads(cleaned[start:end])
    except:
        return {"type": "research", "reason": "defaulting to research"}