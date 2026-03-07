# agent/memory_store.py
# Long-term persistent memory — different from memory.py (which is short-term cache)
#
# memory.py       = cache/    = raw search results, expires 24 hours
# memory_store.py = memory/   = extracted knowledge, expires 30 days

import os
import json
import hashlib
from datetime import datetime, timedelta

MEMORY_DIR = "memory"
MEMORY_TTL = 30  # days before memory expires

os.makedirs(MEMORY_DIR, exist_ok=True)


def _topic_key(topic: str) -> str:
    """
    Convert topic to a safe filename key.
    "AI healthcare India" → "ai_healthcare_india_a3f5bc.json"
    """
    safe  = "".join(c if c.isalnum() else "_" for c in topic.lower())[:40]
    short = hashlib.md5(topic.lower().encode()).hexdigest()[:6]
    return f"{safe}_{short}.json"


def save_memory(topic: str, facts: dict) -> None:
    """
    Save extracted facts to long-term memory.
    If memory already exists for this topic,
    MERGE new facts with old ones — don't overwrite.
    """
    key      = _topic_key(topic)
    filepath = os.path.join(MEMORY_DIR, key)

    # Load existing memory if it exists
    existing = _load_raw(filepath)

    if existing:
        merged = _merge_memories(existing["facts"], facts)
        print(f"  🧠 Memory updated: {topic[:40]}")
    else:
        merged = facts
        print(f"  🧠 Memory created: {topic[:40]}")

    memory_entry = {
        "topic":        topic,
        "created_at":   existing.get("created_at", datetime.now().isoformat()) if existing else datetime.now().isoformat(),
        "updated_at":   datetime.now().isoformat(),
        "access_count": (existing.get("access_count", 0) + 1) if existing else 1,
        "facts":        merged
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(memory_entry, f, indent=2, ensure_ascii=False)


def load_memory(topic: str) -> dict | None:
    """
    Try to load memory for a topic.
    Returns None if no memory exists or memory is expired.
    """
    key      = _topic_key(topic)
    filepath = os.path.join(MEMORY_DIR, key)

    raw = _load_raw(filepath)
    if not raw:
        return None

    # Check expiry
    updated = datetime.fromisoformat(raw["updated_at"])
    expires = updated + timedelta(days=MEMORY_TTL)

    if datetime.now() > expires:
        print(f"  ⏰ Memory expired: {topic[:40]}")
        os.remove(filepath)
        return None

    print(f"  🧠 Memory loaded: {topic[:40]} (accessed {raw['access_count']} times)")
    return raw["facts"]


def get_memory_stats() -> dict:
    """
    Show what the agent currently knows.
    Used for the observability dashboard in Upgrade 3.
    """
    files = [f for f in os.listdir(MEMORY_DIR) if f.endswith(".json")]

    topics = []
    for f in files:
        try:
            with open(os.path.join(MEMORY_DIR, f), encoding="utf-8") as fp:
                data = json.load(fp)
                topics.append({
                    "topic":        data.get("topic", "unknown"),
                    "updated_at":   data.get("updated_at", ""),
                    "access_count": data.get("access_count", 0),
                    "companies":    len(data.get("facts", {}).get("companies", []))
                })
        except:
            pass

    return {
        "total_topics":    len(topics),
        "total_companies": sum(t["companies"] for t in topics),
        "topics":          sorted(topics, key=lambda x: x["access_count"], reverse=True)
    }


def _load_raw(filepath: str) -> dict | None:
    """Load raw memory file — returns None if not found."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def _merge_memories(old: dict, new: dict) -> dict:
    """
    Merge two sets of facts intelligently.

    Companies: combine lists, deduplicate by name
               new data overwrites old for same company
    Facts:     combine lists, remove exact duplicates
    """

    # Merge companies — new overwrites old for same name
    old_cos = {c["name"]: c for c in old.get("companies", [])}
    new_cos = {c["name"]: c for c in new.get("companies", [])}
    merged_companies = list({**old_cos, **new_cos}.values())

    # Helper to get text from fact (handles both string and dict formats)
    def fact_text(f): return f.get("fact", f) if isinstance(f, dict) else f
    def challenge_text(c): return c.get("challenge", c) if isinstance(c, dict) else c

    # Merge market facts — no duplicates
    old_facts  = old.get("market_facts", [])
    new_facts  = new.get("market_facts", [])
    old_texts  = {fact_text(f) for f in old_facts}
    merged_facts = old_facts + [f for f in new_facts if fact_text(f) not in old_texts]

    # Merge challenges — no duplicates
    old_challenges = old.get("challenges", [])
    new_challenges = new.get("challenges", [])
    old_ctexts     = {challenge_text(c) for c in old_challenges}
    merged_challenges = old_challenges + [
        c for c in new_challenges if challenge_text(c) not in old_ctexts
    ]

    return {
        "companies":    merged_companies,
        "market_facts": merged_facts,
        "challenges":   merged_challenges
    }