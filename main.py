# main.py

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from agent.planner import plan_research
from agent.async_searcher import search_all 
from agent.extractor import extract_facts
from agent.reporter import generate_report
from agent.memory import get_cache_stats

console = Console()

def main():
    console.print(Panel.fit(
        "🤖 [bold cyan]AI Research Agent[/bold cyan]",
        subtitle="Powered by OpenAI + Tavily"
    ))

    query = console.input("\n[bold yellow]Enter your research topic:[/bold yellow] ")
    console.print(f"\n[green]📋 Planning research for:[/green] {query}\n")

    # ── Phase 1 — Plan ──────────────────────────────
    console.print("[bold cyan]Phase 1 → Planning...[/bold cyan]")
    plan = plan_research(query)
    console.print(f"  Subtopics : {plan['SUBTOPICS']}")
    console.print(f"  Searches  : {plan['SEARCHES']}")

    # ── Phase 2 — Search ─────────────────────────────
    console.print("\n[bold cyan]Phase 2 → Searching the web...[/bold cyan]")
    results = search_all(plan["SEARCHES"])
    console.print(f"  ✅ Collected results for {len(results)} queries")

    # ── Phase 3 — Extract ────────────────────────────
    console.print("\n[bold cyan]Phase 3 → Extracting facts with AI...[/bold cyan]")
    facts = extract_facts(results)
    companies = facts.get("companies", [])
    console.print(f"  ✅ Extracted {len(companies)} companies")

    # ── Phase 4 — Cache Stats ────────────────────────
    stats = get_cache_stats()
    console.print(f"\n[dim]📦 Cache: {stats['cached_queries']} queries stored ({stats['cache_size_kb']}kb)[/dim]")

    # ── Phase 5 — Report ─────────────────────────────
    console.print("\n[bold cyan]Phase 5 → Generating report...[/bold cyan]")
    report = generate_report(query, facts)

    # Display report beautifully in terminal
    console.print("\n")
    console.print(Panel(
        Markdown(report),
        title="📄 [bold green]Research Report[/bold green]",
        border_style="green"
    ))

    console.print(Panel.fit(
        "✅ [bold green]Research Complete![/bold green]\nCheck the [cyan]reports/[/cyan] folder for your saved report.",
        border_style="green"
    ))

if __name__ == "__main__":
    main()