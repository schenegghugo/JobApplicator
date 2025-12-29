import sqlite3
import os
import glob
from rich.console import Console
from rich.prompt import Confirm

console = Console()
DB_PATH = "data/db/jobs.db"
RAW_DIR = "data/raw_jobs"

def run():
    console.print("[bold red]⚠️  WARNING: This will delete ALL scraped jobs and downloaded HTML files![/bold red]")
    
    if not Confirm.ask("Are you sure you want to flush the database?"):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    # 1. Clean Database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs")
        conn.commit()
        conn.close()
        console.print(f"[green]✅ Database flushed ({DB_PATH})[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to clean DB: {e}[/red]")

    # 2. Clean Raw Files
    try:
        files = glob.glob(os.path.join(RAW_DIR, "*.html"))
        for f in files:
            os.remove(f)
        console.print(f"[green]✅ Deleted {len(files)} raw HTML files from {RAW_DIR}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to clean raw files: {e}[/red]")

    console.print("\n[bold cyan]✨ System reset. Ready for a fresh scrape.[/bold cyan]")

if __name__ == "__main__":
    run()
