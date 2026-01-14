import sys
import os
import subprocess
import argparse
import signal
import atexit
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

# Map your actual filenames to the menu steps
SCRIPTS = {
    "scrape": "src/run_scraper.py",
    "details": "src/scrape_details.py",
    "filter": "src/filter_jobs.py",           # (Needs refactoring to accept --profile)
    "generate": "src/generate_application.py",
    "compile": "src/compile_pdfs.py",         # (Needs refactoring to accept --profile)
    "reset": "src/reset_db.py"                # (Needs refactoring to accept --profile)
}

PROFILE_DIR = "config/profiles"

# -----------------------------------------------------------------------------
# CLEANUP LOGIC (KILL OLLAMA CPU THREADS)
# -----------------------------------------------------------------------------

def cleanup_ollama():
    """
    Kills the heavy inference process (ollama_llama_server) to free up 
    CPU/RAM immediately.
    """
    try:
        # -f matches the full command line name
        subprocess.run(["pkill", "-f", "ollama_llama_server"], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL)
    except Exception:
        pass

# Register cleanup hooks
atexit.register(cleanup_ollama)

def signal_handler(sig, frame):
    console.print("\n[yellow]⚠️  Force Quit Detected. Cleaning up Ollama...[/yellow]")
    cleanup_ollama()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_available_profiles():
    """Scans config/profiles/ for valid profile folders."""
    if not os.path.exists(PROFILE_DIR):
        return []
    return [d for d in os.listdir(PROFILE_DIR) 
            if os.path.isdir(os.path.join(PROFILE_DIR, d))]

def print_banner(active_profile=None):
    title = Text("🚀 JOB APPLICATOR", justify="center", style="bold cyan")
    subtitle = Text("Multi-Profile Pipeline", justify="center", style="dim white")
    
    content = [title, "\n", subtitle]
    
    if active_profile:
        profile_text = Text(f"\n👤 Active Profile: {active_profile}", justify="center", style="bold green")
        content.append(profile_text)

    console.print(Panel(Text.assemble(*content), border_style="cyan", expand=False))

def run_script(script_path, profile_name):
    """Runs a python script as a subprocess, passing the profile flag."""
    console.rule(f"[bold yellow]Running {script_path} ({profile_name})[/bold yellow]")
    
    cmd = [sys.executable, script_path, "--profile", profile_name]
    
    try:
        # We use check=False so we can handle the error manually without crashing main
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            console.print(f"\n[bold red]❌ Script exited with error code {result.returncode}.[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to launch script: {e}[/bold red]")
    console.print()

# -----------------------------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Job Application Automation Tool")
    parser.add_argument("--profile", type=str, help="Name of the profile to use (e.g., simon)")
    parser.add_argument("--scrape", action="store_true", help="Run Scraper")
    parser.add_argument("--details", action="store_true", help="Run Details Fetcher")
    parser.add_argument("--generate", action="store_true", help="Generate LaTeX")
    parser.add_argument("--compile", action="store_true", help="Compile PDFs")
    
    args = parser.parse_args()

    # 1. DETERMINE PROFILE
    profiles = get_available_profiles()
    
    if not profiles:
        console.print(f"[bold red]❌ No profiles found in {PROFILE_DIR}![/bold red]")
        console.print("Please create a folder (e.g., config/profiles/simon) with identity.yaml inside.")
        sys.exit(1)

    selected_profile = args.profile

    # If no profile via CLI, and we are in CLI-Action mode, fail or default?
    # Better to fail to avoid accidents.
    if (args.scrape or args.details or args.generate or args.compile) and not selected_profile:
        # Unless there is only one profile, then default to it.
        if len(profiles) == 1:
            selected_profile = profiles[0]
        else:
            console.print("[red]❌ You must specify --profile when using action flags.[/red]")
            console.print(f"Available: {', '.join(profiles)}")
            sys.exit(1)

    # --- CLI ARGUMENT MODE (Non-Interactive) ---
    if args.scrape:
        run_script(SCRIPTS["scrape"], selected_profile)
        return
    if args.details:
        run_script(SCRIPTS["details"], selected_profile)
        return
    if args.generate:
        run_script(SCRIPTS["generate"], selected_profile)
        return
    if args.compile:
        run_script(SCRIPTS["compile"], selected_profile)
        return

    # --- INTERACTIVE MENU MODE ---
    
    # If no profile selected yet, ask now
    if not selected_profile:
        console.clear()
        print_banner()
        selected_profile = Prompt.ask("Select Profile", choices=profiles, default=profiles[0])

    while True:
        console.clear()
        print_banner(selected_profile)
        
        console.print("[1] [green]🕷️  Run Scraper[/green]         (src/run_scraper.py)")
        console.print("[2] [blue]🔎 Scrape Details[/blue]      (src/scrape_details.py)")
        console.print("[3] [yellow]🧹 Filter/Curate Jobs[/yellow]  (src/filter_jobs.py)")
        console.print("[4] [magenta]✍️  Generate LaTeX[/magenta]      (src/generate_application.py)")
        console.print("[5] [red]📄 Compile PDFs[/red]        (src/compile_pdfs.py)")
        console.print() 
        console.print("[9] [dim]🧨 Reset Database[/dim]      (src/reset_db.py)")
        console.print("[0] Exit")
        
        try:
            choice = Prompt.ask("\nChoose an action", choices=["1", "2", "3", "4", "5", "9", "0"], default="0")
            
            if choice == "0":
                console.print("[cyan]Bye! 👋[/cyan]")
                cleanup_ollama()
                sys.exit(0)
                
            elif choice == "1":
                run_script(SCRIPTS["scrape"], selected_profile)
                Prompt.ask("Press Enter to continue...")
                
            elif choice == "2":
                run_script(SCRIPTS["details"], selected_profile)
                Prompt.ask("Press Enter to continue...")
                
            elif choice == "3":
                # NOTE: You will need to update filter_jobs.py to accept --profile!
                run_script(SCRIPTS["filter"], selected_profile)
                Prompt.ask("Press Enter to continue...")
                
            elif choice == "4":
                run_script(SCRIPTS["generate"], selected_profile)
                Prompt.ask("Press Enter to continue...")
                
            elif choice == "5":
                # NOTE: You will need to update compile_pdfs.py to accept --profile!
                run_script(SCRIPTS["compile"], selected_profile)
                Prompt.ask("Press Enter to continue...")
                
            elif choice == "9":
                if Prompt.ask(f"[bold red]Delete ALL data for '{selected_profile}'?[/bold red]", choices=["y", "n"]) == "y":
                    run_script(SCRIPTS["reset"], selected_profile)
                    Prompt.ask("Press Enter to continue...")
                    
        except KeyboardInterrupt:
            cleanup_ollama()
            sys.exit(0)

if __name__ == "__main__":
    main()
