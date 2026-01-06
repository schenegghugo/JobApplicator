import sys
import os
import yaml
import sqlite3
import hashlib
from rich.console import Console
from playwright.sync_api import sync_playwright

# Ensure imports work from project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.scrapers.dispatcher import detect_ats
# IMPORT PARSE_SIMPLE FROM UNIFIED PARSER NOW
from src.scrapers.unified_parser import parse_simple

console = Console()
DB_PATH = "data/db/jobs.db"
CONFIG_PATH = "config/targets.yaml"

def load_targets():
    if not os.path.exists(CONFIG_PATH):
        console.print(f"[red]❌ Config not found: {CONFIG_PATH}[/red]")
        return []
        
    with open(CONFIG_PATH, 'r') as f:
        data = yaml.safe_load(f)
    
    all_urls = []
    if isinstance(data, dict):
        for group, urls in data.items():
            if isinstance(urls, list):
                all_urls.extend(urls)
    elif isinstance(data, list):
        all_urls = data
        
    return list(set(all_urls))

def save_to_db(jobs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for job in jobs:
        # Create a unique ID based on the specific job URL
        job_id = hashlib.md5(job.url.encode('utf-8')).hexdigest()
        
        try:
            cursor.execute('''
                INSERT INTO jobs (id, company, ats_provider, title, location, apply_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, 
                job.company, 
                job.ats_provider, 
                job.title, 
                job.location, 
                job.url, 
                'new'
            ))
            if cursor.rowcount > 0:
                new_count += 1
        except sqlite3.IntegrityError:
            pass # Job already exists
            
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
    console.print(f"[bold cyan]🚀 Starting Smart Scraper with Dispatcher for {len(targets)} sites...[/bold cyan]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                
                # Lazy load handling
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000) 

                content = page.content()
                jobs = []
                
                # --- DISPATCHER LOGIC ---
                detection = detect_ats(url)
                
                if detection:
                    # Specific ATS detected
                    parser_func, ats_name = detection
                    
                    # CALL WITH 3 ARGUMENTS (Standardized in unified_parser)
                    jobs = parser_func(content, company_name, url)
                    parser_used = ats_name
                else:
                    # Fallback to Simple/HTML
                    jobs = parse_simple(content, company_name, url)
                    parser_used = "Simple/HTML"

                # --- SAVE RESULTS ---
                if jobs:
                    new_jobs = save_to_db(jobs)
                    total_new += new_jobs
                    color = "green" if new_jobs > 0 else "yellow"
                    console.print(f"      ✅ Parsed via [cyan]{parser_used}[/cyan]. Found {len(jobs)}. [{color}]New: {new_jobs}[/{color}]")
                else:
                    console.print(f"[dim]      ❌ No jobs found via {parser_used}.[/dim]")

            except Exception as e:
                console.print(f"[red]      ❌ Error: {e}[/red]")
            finally:
                page.close()

        browser.close()

    console.print(f"\n[bold green]✨ Run complete! Total new jobs: {total_new}[/bold green]")

if __name__ == "__main__":
    run()
