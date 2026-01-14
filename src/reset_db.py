import sqlite3
import os
import sys
import glob
import argparse
from rich.console import Console
from rich.prompt import Confirm

# Ensure imports work from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.paths import get_profile_paths

console = Console()

def run(profile_name):
    # 1. Resolve Profile Paths
    paths = get_profile_paths(profile_name)
    db_path = paths["db_file"]
    raw_dir = paths["raw_html_dir"]

    console.print(f"[bold red]⚠️  WARNING: This will delete ALL scraped jobs and raw HTML files for profile: '{profile_name}'[/bold red]")
    console.print(f"[dim]   Database: {db_path}[/dim]")
    console.print(f"[dim]   Raw Dir:  {raw_dir}[/dim]")
    
    if not Confirm.ask(f"Are you sure you want to flush data for '{profile_name}'?"):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    # 2. Clean Database
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # We delete rows instead of the file to preserve the table structure/schema
            cursor.execute("DELETE FROM jobs")
            conn.commit()
            # Optional: vacuum to reclaim space
            cursor.execute("VACUUM") 
            conn.close()
            console.print(f"[green]✅ Database flushed ({os.path.basename(db_path)})[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to clean DB: {e}[/red]")
    else:
        console.print(f"[yellow]⚠️  Database file not found, skipping.[/yellow]")

    # 3. Clean Raw Files
    if os.path.exists(raw_dir):
        try:
            files = glob.glob(os.path.join(raw_dir, "*.html"))
            if files:
                for f in files:
                    os.remove(f)
                console.print(f"[green]✅ Deleted {len(files)} raw HTML files[/green]")
            else:
                console.print("[dim]   No raw files found to delete.[/dim]")
        except Exception as e:
            console.print(f"[red]❌ Failed to clean raw files: {e}[/red]")
    else:
        console.print(f"[yellow]⚠️  Raw directory does not exist, skipping.[/yellow]")

    console.print(f"\n[bold cyan]✨ Profile '{profile_name}' reset. Ready for a fresh scrape.[/bold cyan]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=str, required=True, help="Profile name")
    args = parser.parse_args()
    
    run(args.profile)
