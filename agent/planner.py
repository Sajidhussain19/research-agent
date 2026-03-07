# agent/planner.py

from utils.ai_client import ask_ai   # ← changed this line

def plan_research(query: str) -> dict:
    system = """You are a research planning expert. 
    When given a research topic, you break it down into 
    specific search queries and subtopics.
    Always respond in this exact format:
    
    SUBTOPICS: topic1, topic2, topic3
    SEARCHES: search query 1 | search query 2 | search query 3
    REPORT_TYPE: market_research
    """
    
    prompt = f"Plan research for this topic: {query}"
    response = ask_ai(prompt, system)   # ← changed this line
    
    # Parse the structured response
    plan = {}
    for line in response.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            plan[key.strip()] = value.strip()
    
    plan["SUBTOPICS"] = [s.strip() for s in plan.get("SUBTOPICS", "").split(",")]
    plan["SEARCHES"] = [s.strip() for s in plan.get("SEARCHES", "").split("|")]
    
    return plan