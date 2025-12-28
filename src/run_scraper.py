import sys
import os

# Ensure we can import modules from src/ regardless of execution context
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import yaml
import sqlite3
import hashlib
from rich.console import Console
from playwright.sync_api import sync_playwright

# Correct absolute import based on the sys.path modification
from src.scrapers.parsers.teamtailor import parse_teamtailor

console = Console()
DB_PATH = "data/db/jobs.db"
CONFIG_PATH = "config/targets.yaml"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_to_db(jobs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for job in jobs:
        job_id = hashlib.md5(job.url.encode('utf-8')).hexdigest()
        try:
            cursor.execute('''
                INSERT INTO jobs (id, company, ats_provider, title, location, apply_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, job.company, job.ats_provider, job.title, job.location, job.url, 'new'))
            new_count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return new_count

def run():
    config = load_config()
    targets = config.get('teamtailor', [])
    
    console.print(f"[bold cyan]🚀 Starting Scraper (Powered by Playwright) for {len(targets)} sites...[/bold cyan]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        total_found = 0

        for url in targets:
            try:
                # Company Name Logic
                try:
                    company_name = url.split('//')[1].split('.')[0]
                    if company_name in ['jobs', 'career', 'careers']:
                        company_name = url.split('//')[1].split('.')[1]
                except:
                    company_name = "unknown"

                console.print(f"   🔎 Scraping [bold]{company_name}[/bold]...")
                
                page = context.new_page()
                try:
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000) # Small breath
                    
                    content = page.content()
                    jobs = parse_teamtailor(content, company_name)
                    new_jobs = save_to_db(jobs)
                    
                    color = "green" if new_jobs > 0 else "yellow"
                    console.print(f"      ↳ Found {len(jobs)} jobs. [{color}]New: {new_jobs}[/{color}]")
                    total_found += new_jobs
                    
                except Exception as e:
                    console.print(f"[red]      ❌ Failed to load page: {e}[/red]")
                finally:
                    page.close()
                    
            except Exception as e:
                console.print(f"[red]      ❌ Critical Error: {e}[/red]")

        browser.close()

    console.print(f"\n[bold green]✨ Done! Total new jobs saved: {total_found}[/bold green]")

if __name__ == "__main__":
    run()
