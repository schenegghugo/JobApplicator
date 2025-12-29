import sqlite3
import re
from rich.console import Console
from rich.table import Table
from typing import Tuple, Set

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

DB_PATH = "data/db/jobs.db"
console = Console()

POSITIVE_KEYWORDS = {
    "pipeline", "td", "technical", "python", "coordinator", 
    "assistant", "runner", "atd", "mid", "automation", "tools",
    "developer", "data", "analyst", "programmer", "engineer", "devops", "software" # Added a few common ones
}

NEGATIVE_KEYWORDS = {
    "senior", "lead", "supervisor", "principal", "head", "chief",
    "finance", "hr", "legal", "accountant", "marketing", "sales",
    "art", "lighter", "animator", "modeler", "compositor", "Java", "concept", "JavaScript", 
    "rigger", "fx" # Unless you want FX TD roles, keep FX here or move to positive
}

# -----------------------------------------------------------------------------
# UTILS
# -----------------------------------------------------------------------------

def migrate_db(cursor):
    """Adds new columns if they don't exist yet."""
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN relevance_score INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE jobs ADD COLUMN decision_reason TEXT")
        console.print("[green]✨ Added new columns to database schema.[/green]")
    except sqlite3.OperationalError:
        # Columns likely already exist
        pass

def tokenize(text: str) -> Set[str]:
    """Tokenize a string into lowercase word tokens."""
    if not text: return set()
    return set(re.findall(r"\b\w+\b", text.lower()))

def classify_job(title: str) -> Tuple[str, int, str]:
    tokens = tokenize(title)

    negative_hits = tokens & NEGATIVE_KEYWORDS
    if negative_hits:
        return (
            "ignored",
            0,
            f"Negative match: {', '.join(sorted(negative_hits))}"
        )

    positive_hits = tokens & POSITIVE_KEYWORDS
    if positive_hits:
        return (
            "approved",
            len(positive_hits),
            f"Positive match: {', '.join(sorted(positive_hits))}"
        )

    return (
        "ignored",
        0,
        "No keywords matched"
    )

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def run() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Ensure DB has the new columns
    migrate_db(cursor)

    # 2. Get Scraped Jobs
    cursor.execute("SELECT id, title, company FROM jobs WHERE status = 'scraped'")
    jobs = cursor.fetchall()

    if not jobs:
        console.print("[yellow]No scraped jobs to filter.[/yellow]")
        return

    approved_count = 0
    ignored_count = 0

    table = Table(title="Job Triage Results")
    table.add_column("Company", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Reason", style="dim")

    for job in jobs:
        status, score, reason = classify_job(job["title"])

        if status == "approved":
            approved_count += 1
            color = "green"
        else:
            ignored_count += 1
            color = "red"

        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, relevance_score = ?, decision_reason = ?
            WHERE id = ?
            """,
            (status, score, reason, job["id"])
        )

        table.add_row(
            job["company"],
            job["title"],
            f"[{color}]{status}[/{color}]",
            str(score),
            reason,
        )

    conn.commit()
    conn.close()

    console.print(table)
    console.print(
        f"\n[green]✅ Approved: {approved_count}[/green] | "
        f"[red]❌ Ignored: {ignored_count}[/red]"
    )

if __name__ == "__main__":
    run()
