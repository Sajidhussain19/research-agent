# agent/planner.py

from utils.ai_client import ask_ai
import datetime

def plan_research(query: str) -> dict:
    current_year = datetime.datetime.now().year  # always stays current

    system = f"""You are a research planning expert.
When given a research topic, break it down into specific search queries and subtopics.
Today's year is {current_year}. Always use {current_year} in ALL search queries — never use older years.
Always respond in this exact format:

SUBTOPICS: topic1, topic2, topic3
SEARCHES: search query {current_year} | search query {current_year} | search query {current_year}
REPORT_TYPE: market_research"""

    prompt = f"Plan research for this topic: {query}\nRemember: use {current_year} in every search query."
    response = ask_ai(prompt, system)

    plan = {}
    for line in response.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            plan[key.strip()] = value.strip()

    plan["SUBTOPICS"] = [s.strip() for s in plan.get("SUBTOPICS", "").split(",")]
    plan["SEARCHES"]  = [s.strip() for s in plan.get("SEARCHES",  "").split("|")]

    return plan