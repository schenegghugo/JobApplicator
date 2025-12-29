import sys
import os
import yaml
import sqlite3
import hashlib
from rich.console import Console
from playwright.sync_api import sync_playwright

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.scrapers.parsers.teamtailor import parse_teamtailor
from src.scrapers.parsers.greenhouse import parse_greenhouse
from src.scrapers.parsers.lever import parse_lever
from src.scrapers.parsers.ashby import parse_ashby
from src.scrapers.parsers.simple import parse_simple

console = Console()
DB_PATH = "data/db/jobs.db"
CONFIG_PATH = "config/targets.yaml"

def load_targets():
    with open(CONFIG_PATH, 'r') as f:
        data = yaml.safe_load(f)
    all_urls = []
    for group, urls in data.items():
        if isinstance(urls, list):
            all_urls.extend(urls)
    return list(set(all_urls))

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

def derive_company_name(url):
    try:
        if "ilpvfx" in url: return "ilp"
        if "fablefx" in url: return "fablefx"
        if "filmgate" in url: return "filmgate"
        
        parts = url.split('//')[1].split('.')
        if parts[0] in ['jobs', 'careers', 'career', 'www']:
            return parts[1]
        return parts[0]
    except:
        return "unknown"

def run():
    targets = load_targets()
    console.print(f"[bold cyan]🚀 Starting Smart Scraper for {len(targets)} sites...[/bold cyan]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # --- FIX 1: IGNORE SSL ERRORS ---
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        total_new = 0

        for url in targets:
            company_name = derive_company_name(url)
            console.print(f"   🔎 Visiting [bold]{company_name}[/bold]...")
            
            page = context.new_page()
            try:
                # --- FIX 2: ROBUST NAVIGATION ---
                # Increased timeout to 45s for roaming
                # Using 'commit' instead of 'domcontentloaded' sometimes helps with redirects
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                
                # Scroll to bottom to trigger lazy loading (Fixes Starbreeze)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000) 

                content = page.content()
                jobs = []
                parser_used = "none"

                # 1. Teamtailor
                if not jobs:
                    jobs = parse_teamtailor(content, company_name)
                    if jobs: parser_used = "Teamtailor"

                # 2. Greenhouse
                if not jobs:
                    jobs = parse_greenhouse(content, company_name)
                    if jobs: parser_used = "Greenhouse"

                # 3. Lever
                if not jobs:
                    jobs = parse_lever(content, company_name)
                    if jobs: parser_used = "Lever"

                # 4. Ashby
                if not jobs:
                    jobs = parse_ashby(content, company_name)
                    if jobs: parser_used = "Ashby"

                # 5. Simple HTML
                if not jobs:
                    jobs = parse_simple(content, company_name, url)
                    if jobs: parser_used = "Simple/HTML"

                if jobs:
                    new_jobs = save_to_db(jobs)
                    total_new += new_jobs
                    color = "green" if new_jobs > 0 else "yellow"
                    console.print(f"      ✅ Parsed via [cyan]{parser_used}[/cyan]. Found {len(jobs)}. [{color}]New: {new_jobs}[/{color}]")
                else:
                    console.print(f"[dim]      ❌ No jobs found with any parser.[/dim]")

            except Exception as e:
                console.print(f"[red]      ❌ Error: {e}[/red]")
            finally:
                page.close()

        browser.close()

    console.print(f"\n[bold green]✨ Run complete! Total new jobs: {total_new}[/bold green]")

if __name__ == "__main__":
    run()
