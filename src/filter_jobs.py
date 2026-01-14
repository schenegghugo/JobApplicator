import sqlite3
import re
import os
import sys
import argparse
import yaml
from rich.console import Console
from rich.table import Table
from typing import Tuple, Set

# Ensure imports work from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.paths import get_profile_paths

console = Console()

# -----------------------------------------------------------------------------
# UTILS
# -----------------------------------------------------------------------------

def load_keywords(strategy_path: str) -> Tuple[Set[str], Set[str]]:
    """
    Loads keywords from the profile's strategy.yaml.
    Adapts to the structure:
      job_filtering:
        positive_keywords: [...]
        negative_keywords: [...]
    """
    pos_keywords = set()
    neg_keywords = set()

    if os.path.exists(strategy_path):
        try:
            with open(strategy_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                
            # Look for the 'job_filtering' block
            section = data.get('job_filtering', {})
            
            # Retrieve lists (handling cases where they might be None)
            pos_list = section.get('positive_keywords') or []
            neg_list = section.get('negative_keywords') or []

            # Normalize to lowercase sets
            pos_keywords = {str(w).lower() for w in pos_list if w}
            neg_keywords = {str(w).lower() for w in neg_list if w}
                
            console.print(f"[dim]Loaded strategy: {len(pos_keywords)} positive, {len(neg_keywords)} negative keywords.[/dim]")
            
        except Exception as e:
            console.print(f"[red]Failed to load strategy keywords: {e}[/red]")
    else:
        console.print(f"[yellow]⚠️ Strategy file not found at: {strategy_path}[/yellow]")

    return pos_keywords, neg_keywords

def migrate_db(cursor):
    """Adds new columns if they don't exist yet."""
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN relevance_score INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE jobs ADD COLUMN decision_reason TEXT")
    except sqlite3.OperationalError:
        pass

def tokenize(text: str) -> Set[str]:
    """Tokenize a string into lowercase word tokens."""
    if not text: return set()
    # \w+ matches words including alphanumeric and underscore.
    # We lower() to ensure case-insensitive matching.
    return set(re.findall(r"\b\w+\b", text.lower()))

def classify_job(title: str, pos_keywords: Set[str], neg_keywords: Set[str]) -> Tuple[str, int, str]:
    """
    Classifies a job based on strict set intersection.
    1. If ANY negative keyword matches -> Ignored.
    2. If NO positive keywords match -> Ignored (Strict mode).
    3. If ANY positive keyword matches -> Approved.
    """
    tokens = tokenize(title)

    # 1. Check Negatives
    negative_hits = tokens & neg_keywords
    if negative_hits:
        return (
            "ignored",
            0,
            f"Negative match: {', '.join(sorted(negative_hits))}"
        )

    # 2. Check Positives
    positive_hits = tokens & pos_keywords
    
    if positive_hits:
        return (
            "approved",
            len(positive_hits),
            f"Positive match: {', '.join(sorted(positive_hits))}"
        )

    # 3. No match
    if not pos_keywords:
        return ("ignored", 0, "Strategy has no positive keywords")
    
    return (
        "ignored",
        0,
        "No keywords matched"
    )

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def run(profile_name):
    # 1. Setup Paths
    paths = get_profile_paths(profile_name)
    db_path = paths["db_file"]
    
    if not os.path.exists(db_path):
        console.print(f"[red]❌ Database not found for {profile_name}[/red]")
        return

    # 2. Load Keywords (Profile Dependent)
    pos_keywords, neg_keywords = load_keywords(paths["strategy_file"])

    if not pos_keywords:
        console.print("[yellow]⚠️ Warning: No positive keywords found in 'job_filtering' section of strategy.yaml.[/yellow]")
        console.print("[dim]   (Strict Mode: All jobs will be ignored without positive matches)[/dim]")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 3. Ensure DB Schema
    migrate_db(cursor)

    # 4. Get Scraped Jobs
    cursor.execute("SELECT id, title, company FROM jobs WHERE status = 'scraped'")
    jobs = cursor.fetchall()

    if not jobs:
        console.print(f"[yellow]No 'scraped' jobs found in database for {profile_name}.[/yellow]")
        console.print("[dim]Run the scraper first (Action 3).[/dim]")
        return

    console.print(f"[bold cyan]🧹 Filtering {len(jobs)} jobs for [white]{profile_name}[/white]...[/bold cyan]")

    approved_count = 0
    ignored_count = 0

    table = Table(title=f"Job Triage ({profile_name})")
    table.add_column("Company", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Reason", style="dim")

    for job in jobs:
        status, score, reason = classify_job(job["title"], pos_keywords, neg_keywords)

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=str, required=True, help="Profile name")
    args = parser.parse_args()
    
    run(args.profile)
