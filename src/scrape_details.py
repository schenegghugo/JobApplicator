import sqlite3
import os
import re
from rich.console import Console
from rich.progress import track
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

console = Console()
DB_PATH = "data/db/jobs.db"
RAW_DIR = "data/raw_jobs"

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

def get_new_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE description IS NULL AND status != 'ignored'")
    jobs = cursor.fetchall()
    conn.close()
    return jobs

def update_job_description(job_id, description, raw_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs 
        SET description = ?, status = 'scraped', apply_url = ? 
        WHERE id = ?
    """, (description, raw_path, job_id)) # Note: Storing path helps debug, though URL is standard
    conn.commit()
    conn.close()

def run():
    jobs = get_new_jobs()
    if not jobs:
        console.print("[yellow]No pending jobs to scrape details for.[/yellow]")
        return

    console.print(f"[bold cyan]🚀 Fetching details for {len(jobs)} jobs...[/bold cyan]")
    console.print(f"[dim]Network Timeout set to 45s for roaming connection[/dim]")

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
                    
                    # --- NEW FILENAME LOGIC ---
                    clean_company = sanitize_filename(job['company'])
                    clean_title = sanitize_filename(job['title'])
                    clean_loc = sanitize_filename(job['location'])
                    # We keep the hash at the end to prevent overwriting if two jobs have same name
                    short_id = job['id'][:6] 
                    
                    filename = f"{clean_company}__{clean_title}__{clean_loc}__{short_id}.html"
                    filepath = os.path.join(RAW_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    update_job_description(job['id'], text_content, filepath)
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
    run()
