import sqlite3
import os
import re
import argparse
import sys
from rich.console import Console
from rich.progress import track
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# Ensure imports work from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.paths import get_profile_paths, ensure_dirs

console = Console()

def sanitize_filename(text):
    """
    Turns "Senior C++ Developer (Stockholm)" into "Senior_C_Developer_Stockholm"
    Removes special chars and spaces.
    """
    if not text:
        return "Unknown"
    # Replace non-alphanumeric chars with underscore
    clean = re.sub(r'[^\w\-_]', '_', text)
    # Remove multiple underscores
    clean = re.sub(r'_+', '_', clean)
    return clean.strip('_')

def get_new_jobs(db_path):
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Check for jobs that are new OR failed previously (optional logic)
    cursor.execute("SELECT * FROM jobs WHERE description IS NULL AND status != 'ignored'")
    jobs = cursor.fetchall()
    conn.close()
    return jobs

def update_job_description(db_path, job_id, description, raw_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET description = ?, status = 'scraped', apply_url = ? 
        WHERE id = ?
    """, (description, raw_path, job_id)) 
    conn.commit()
    conn.close()

def run(profile_name):
    # 1. Resolve Profile Paths
    paths = get_profile_paths(profile_name)
    ensure_dirs(paths)
    
    db_path = paths["db_file"]
    raw_dir = paths["raw_html_dir"]

    # 2. Get Jobs
    jobs = get_new_jobs(db_path)
    if not jobs:
        console.print(f"[yellow]No pending jobs to scrape details for profile: {profile_name}[/yellow]")
        return

    console.print(f"[bold cyan]🚀 Fetching details for {len(jobs)} jobs ([white]{profile_name}[/white])...[/bold cyan]")
    console.print(f"[dim]   📂 Saving Raw HTML to: {raw_dir}[/dim]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        for job in track(jobs, description="Scraping..."):
            page = context.new_page()
            
            for attempt in range(2):
                try:
                    page.goto(job['apply_url'], timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)

                    html = page.content()
                    soup = BeautifulSoup(html, 'lxml')
                    text_content = soup.get_text(separator='\n', strip=True)
                    
                    # --- FILENAME LOGIC ---
                    clean_company = sanitize_filename(job['company'])
                    clean_title = sanitize_filename(job['title'])
                    clean_loc = sanitize_filename(job['location'])
                    short_id = job['id'][:6] 
                    
                    filename = f"{clean_company}__{clean_title}__{clean_loc}__{short_id}.html"
                    # Save to Profile-Specific Raw Directory
                    filepath = os.path.join(raw_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    update_job_description(db_path, job['id'], text_content, filepath)
                    break
                    
                except PlaywrightTimeout:
                    if attempt == 1:
                        console.print(f"[red]❌ Timeout on {job['company']} (Skipping)[/red]")
                except Exception as e:
                    console.print(f"[red]❌ Error on {job['apply_url']}: {e}[/red]")
                    break
            
            page.close()
        
        browser.close()

    console.print("[bold green]✨ Detailed scrape complete![/bold green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=str, required=True, help="Profile name (e.g., hugo, simon)")
    args = parser.parse_args()
    
    run(args.profile)
