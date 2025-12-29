import sys
import subprocess
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()

# Map your actual filenames to the menu steps
SCRIPTS = {
    "scrape": "src/run_scraper.py",
    "details": "src/scrape_details.py",
    "filter": "src/filter_jobs.py",  # Assuming this is your curation/filtering step
    "generate": "src/generate_application.py",
    "compile": "src/compile_pdfs.py",
    "reset": "src/reset_db.py"
}

def print_banner():
    title = Text("🚀 JOB APPLICATOR", justify="center", style="bold cyan")
    subtitle = Text("Automated Pipeline", justify="center", style="dim white")
    console.print(Panel(Text.assemble(title, "\n", subtitle), border_style="cyan", expand=False))

def run_script(script_path):
    """Runs a python script as a subprocess."""
    console.rule(f"[bold yellow]Running {script_path}[/bold yellow]")
    try:
        # sys.executable ensures we use the current venv python
        result = subprocess.run([sys.executable, script_path])
        if result.returncode != 0:
            console.print(f"\n[bold red]❌ Script {script_path} exited with error.[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to launch script: {e}[/bold red]")
    console.print()

def main():
    parser = argparse.ArgumentParser(description="Job Application Automation Tool")
    parser.add_argument("--scrape", action="store_true", help="Run Scraper")
    parser.add_argument("--generate", action="store_true", help="Generate LaTeX")
    parser.add_argument("--compile", action="store_true", help="Compile PDFs")
    
    args = parser.parse_args()

    # --- CLI MODE ---
    if args.scrape:
        run_script(SCRIPTS["scrape"])
        return
    if args.generate:
        run_script(SCRIPTS["generate"])
        return
    if args.compile:
        run_script(SCRIPTS["compile"])
        return

    # --- INTERACTIVE MENU MODE ---
    while True:
        console.clear()
        print_banner()
        
        console.print("[1] [green]🕷️  Run Scraper[/green]         (src/run_scraper.py)")
        console.print("[2] [blue]🔎 Scrape Details[/blue]      (src/scrape_details.py)")
        console.print("[3] [yellow]🧹 Filter/Curate Jobs[/yellow]  (src/filter_jobs.py)")
        console.print("[4] [magenta]✍️  Generate LaTeX[/magenta]      (src/generate_application.py)")
        console.print("[5] [red]📄 Compile PDFs[/red]        (src/compile_pdfs.py)")
        console.print() 
        console.print("[9] [dim]🧨 Reset Database[/dim]      (src/reset_db.py)")
        console.print("[0] Exit")
        
        choice = Prompt.ask("\nChoose an action", choices=["1", "2", "3", "4", "5", "9", "0"], default="0")
        
        if choice == "0":
            console.print("[cyan]Bye! 👋[/cyan]")
            sys.exit(0)
        elif choice == "1":
            run_script(SCRIPTS["scrape"])
            Prompt.ask("Press Enter to continue...")
        elif choice == "2":
            run_script(SCRIPTS["details"])
            Prompt.ask("Press Enter to continue...")
        elif choice == "3":
            run_script(SCRIPTS["filter"])
            Prompt.ask("Press Enter to continue...")
        elif choice == "4":
            run_script(SCRIPTS["generate"])
            Prompt.ask("Press Enter to continue...")
        elif choice == "5":
            run_script(SCRIPTS["compile"])
            Prompt.ask("Press Enter to continue...")
        elif choice == "9":
            if Prompt.ask("[red]Are you sure you want to delete all data?[/red]", choices=["y", "n"]) == "y":
                run_script(SCRIPTS["reset"])
                Prompt.ask("Press Enter to continue...")

if __name__ == "__main__":
    main()
