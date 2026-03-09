# agent/arxiv_searcher.py
# Searches ArXiv for academic papers related to the research query
# Only returns papers if they are actually relevant to the topic

import arxiv
import asyncio


def _clean_query(queries: list[str], original_query: str) -> str:
    """
    Build a clean ArXiv search query from the original user query.
    - Strips year numbers (2026, 2025 etc) — ArXiv uses its own date filtering
    - Strips filler words
    - Uses the core topic words only
    """
    import re

    # Use original query as base — it's cleaner than planner queries
    q = original_query.lower()

    # Remove years
    q = re.sub(r'\b20\d{2}\b', '', q)

    # Remove filler phrases
    fillers = [
        "what is", "what are", "how does", "how do", "how is",
        "explain", "top companies", "best companies", "companies using",
        "latest", "recent", "in india", "and", "the", "a ", " a",
        "?", "!", "using", "with", "for"
    ]
    for f in fillers:
        q = q.replace(f, " ")

    # Clean up extra spaces
    q = " ".join(q.split()).strip()

    # Fallback to first planner query if clean query is too short
    if len(q) < 4 and queries:
        fallback = re.sub(r'\b20\d{2}\b', '', queries[0])
        q = " ".join(fallback.split()).strip()

    return q


def _is_relevant(paper, topic_words: list[str]) -> bool:
    """
    Check if a paper is actually relevant to the topic.
    At least one topic word must appear in title or summary.
    """
    text = (paper.title + " " + paper.summary).lower()
    return any(word.lower() in text for word in topic_words)


def _search_arxiv_sync(query: str, original_query: str, max_results: int = 8) -> list[dict]:
    """
    Blocking ArXiv search with relevance filtering.
    """
    import re

    # Extract topic keywords from original query for relevance check
    stop_words = {"what","is","are","how","does","do","top","best","companies",
                  "using","explain","latest","recent","and","the","a","in","of",
                  "for","with","their","its"}
    topic_words = [
        w for w in re.sub(r'[^a-z0-9 ]', '', original_query.lower()).split()
        if w not in stop_words and len(w) > 2
    ]

    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query       = query,
            max_results = max_results,
            sort_by     = arxiv.SortCriterion.Relevance,  # ← Relevance, not date
        )

        papers = []
        for r in client.results(search):
            # Skip if not relevant to the actual topic
            if not _is_relevant(r, topic_words):
                continue

            papers.append({
                "title":     r.title,
                "authors":   ", ".join(a.name for a in r.authors[:3])
                             + (" et al." if len(r.authors) > 3 else ""),
                "summary":   r.summary[:300].replace("\n", " ") + "...",
                "url":       r.entry_id,
                "pdf_url":   r.pdf_url,
                "published": r.published.strftime("%Y-%m-%d") if r.published else "",
                "category":  r.primary_category,
            })

            if len(papers) >= 4:  # Stop after 4 relevant papers
                break

        return papers

    except Exception as e:
        print(f"  [ArXiv Error] {e}")
        return []


async def search_arxiv_async(queries: list[str], original_query: str = "") -> list[dict]:
    """
    Searches ArXiv with a clean, relevant query.
    Falls back to empty list gracefully if no relevant papers found.
    """
    if not queries:
        return []

    # Build a clean topic-focused query
    clean_q = _clean_query(queries, original_query or queries[0])

    print(f"  📄 ArXiv search: '{clean_q}' (from: '{(original_query or queries[0])[:40]}')")

    loop   = asyncio.get_event_loop()
    papers = await loop.run_in_executor(
        None, _search_arxiv_sync, clean_q, original_query or queries[0], 8
    )

    print(f"  📄 ArXiv: {len(papers)} relevant papers found")
    return papers