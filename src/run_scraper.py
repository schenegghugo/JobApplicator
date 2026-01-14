import sys
import os
import yaml
import sqlite3
import hashlib
import argparse
from rich.console import Console
from playwright.sync_api import sync_playwright, Error as PlaywrightError

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.scrapers.dispatcher import detect_ats
from src.scrapers.unified_parser import parse_simple
from src.utils.paths import get_profile_paths, ensure_dirs

console = Console()

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY,
          company TEXT,
          ats_provider TEXT,
          title TEXT,
          location TEXT,
          apply_url TEXT,
          description TEXT,
          status TEXT DEFAULT 'new',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def load_targets(config_path):
    if not os.path.exists(config_path):
        console.print(f"[red]❌ Config not found: {config_path}[/red]")
        return []
        
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    all_urls = []
    if isinstance(data, dict):
        for group, urls in data.items():
            if isinstance(urls, list):
                all_urls.extend(urls)
    elif isinstance(data, list):
        all_urls = data
        
    return list(set(all_urls))

def save_to_db(jobs, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    new_count = 0
    for job in jobs:
        job_id = hashlib.md5(job.url.encode('utf-8')).hexdigest()
        try:
            cursor.execute('''
                INSERT INTO jobs (id, company, ats_provider, title, location, apply_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, job.company, job.ats_provider, job.title, job.location, job.url, 'new'
            ))
            if cursor.rowcount > 0:
                new_count += 1
        except sqlite3.IntegrityError:
            pass 
    conn.commit()
    conn.close()
    return new_count

def derive_company_name(url):
    try:
        parts = url.split('//')[1].split('.')
        # Handle cases like careers.google.com vs google.com/careers
        if len(parts) > 2:
            return parts[1] # e.g. jobs.bouygues.com -> bouygues
        if parts[0] in ['jobs', 'careers', 'www']:
            return parts[1]
        return parts[0]
    except:
        return "unknown"

def run(profile_name):
    paths = get_profile_paths(profile_name)
    ensure_dirs(paths)
    
    db_path = paths["db_file"]
    targets_path = paths["targets_file"]

    init_db(db_path)
    targets = load_targets(targets_path)
    
    if not targets:
        console.print(f"[yellow]⚠️ No targets found in {targets_path}[/yellow]")
        return

    console.print(f"[bold cyan]🚀 Starting Scraper for [white]{profile_name}[/white] ({len(targets)} sites)...[/bold cyan]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Increased timeout to 60s for heavy corporate sites
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        total_new = 0

        for url in targets:
            company_name = derive_company_name(url)
            console.print(f"   🔎 Visiting [bold]{company_name}[/bold]...", end="")
            
            page = context.new_page()
            
            # --- ROBUST NAVIGATION ---
            try:
                # 1. Navigate
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                except PlaywrightError as e:
                    console.print(f"\n      [red]❌ Navigation failed: {e.message.splitlines()[0]}[/red]")
                    page.close()
                    continue

                # 2. Scroll (Safe Mode)
                # We wrap this in try/except so if context dies (redirect), we proceed with what we have
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000) 
                except PlaywrightError:
                    # Context destroyed or scroll failed - usually means a redirect happened
                    # or the page is static. We ignore and parse current state.
                    pass

                # 3. Get Content
                try:
                    content = page.content()
                except PlaywrightError:
                    console.print("\n      [red]❌ Context lost during read (Redirect loop?)[/red]")
                    page.close()
                    continue
                
                # 4. Parse
                jobs = []
                detection = detect_ats(url)
                
                if detection:
                    parser_func, ats_name = detection
                    jobs = parser_func(content, company_name, url)
                    parser_used = ats_name
                else:
                    jobs = parse_simple(content, company_name, url)
                    parser_used = "Simple/HTML"

                # 5. Save
                if jobs:
                    new_jobs = save_to_db(jobs, db_path)
                    total_new += new_jobs
                    color = "green" if new_jobs > 0 else "yellow"
                    console.print(f"\r   ✅ [bold]{company_name}[/bold]: Found {len(jobs)} via {parser_used}. [{color}]New: {new_jobs}[/{color}]")
                else:
                    console.print(f"\r   ❌ [bold]{company_name}[/bold]: No jobs found via {parser_used}.")

            except Exception as e:
                console.print(f"\n      [red]❌ Unexpected Error: {e}[/red]")
            finally:
                # Always close the page to free memory
                try:
                    page.close()
                except:
                    pass

        browser.close()

    console.print(f"\n[bold green]✨ Run complete! Total new jobs: {total_new}[/bold green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=str, required=True)
    args = parser.parse_args()
    
    run(args.profile)
