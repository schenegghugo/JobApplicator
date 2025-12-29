import sqlite3
import os
import requests
import re
from rich.console import Console

console = Console()

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

DB_PATH = "data/db/jobs.db"
TEMPLATE_DIR = "data/templates"
OUTPUT_DIR = "data/applications"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

# Timeout in seconds (300s = 5 minutes)
TIMEOUT_SECONDS = 900 

# -----------------------------------------------------------------------------
# CANDIDATE PROFILE
# -----------------------------------------------------------------------------

CANDIDATE_PROFILE = """
Name: Hugo Schenegg
Location: Paris, France
Nationality: French
Languages: French (Native), English (Fluent)
Links: github.com/schenegghugo

Education:
- CGI Filmmaker (M.A. equivalent), Supinfocom Arles (2021)
  Focus: Computer Graphics, 3D pipelines, post-production

Professional Experience:
- Studio Coordinator, MPC Paris (Jan 2022 – Present)
  - Outsourced solutions and vendor coordination
  - Python automation of production workflows
  - Data modeling and reporting (Power BI)
  - Payroll, invoice tracking, resource monitoring
  - Production activity control
  - Pipeline integration support (Meshroom)
  - Liaison between artists and technical teams
  - UNIX/Linux operational knowledge

Technical Skills:
- Python (automation, pipeline tools)
- C++ (graphics foundations)
- OpenGL, Vulkan (personal projects)
- UNIX/Linux, Windows
- Git
- Maya
- Data workflows and reconciliation

Projects:
- GraphicsLab (C++ / OpenGL / Vulkan)
  GitHub: https://github.com/schenegghugo/GraphicsLab
- JobApplicator (Python automation)
  GitHub: https://github.com/schenegghugo/JobApplicator
"""

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_template(name):
    """Reads a template file from data/templates."""
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {path}")
    with open(path, 'r') as f:
        return f.read()

def call_ollama(prompt, context=None):
    """
    Sends a request to the local AI model with a strict timeout.
    """
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "context": context, 
        "options": {
            "num_ctx": 4096,   
            "temperature": 0.7,
            "num_thread": 4    # Keep CPU usage sane
        }    
    }
    try:
        # Added timeout argument here
        response = requests.post(OLLAMA_URL, json=data, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        json_resp = response.json()
        return json_resp['response'], json_resp.get('context')
        
    except requests.exceptions.Timeout:
        console.print(f"[bold red]❌ Timeout! Ollama took longer than {TIMEOUT_SECONDS}s.[/bold red]")
        return None, None
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error: {e}[/bold red]")
        return None, None

def extract_code_blocks(text):
    """
    Robustly extracts the Resume and Cover Letter from the AI response.
    """
    if not text: return None, None

    # 1. Split by the RESUME delimiter
    parts = re.split(r"===\s*RESUME\s*===", text, flags=re.IGNORECASE)
    if len(parts) < 2: 
        return None, None
    
    remainder = parts[1]
    
    # 2. Split by the COVER LETTER delimiter
    subparts = re.split(r"===\s*COVER LETTER\s*===", remainder, flags=re.IGNORECASE)
    if len(subparts) < 2: 
        return None, None
        
    raw_resume = subparts[0]
    raw_cover = subparts[1]
    
    def extract_latex(raw_text):
        start_match = re.search(r"\\documentclass", raw_text)
        end_match = re.search(r"\\end\{document\}", raw_text)
        
        if start_match and end_match:
            return raw_text[start_match.start() : end_match.end()]
        return None
    
    resume_clean = extract_latex(raw_resume)
    cover_clean = extract_latex(raw_cover)
    
    return resume_clean, cover_clean

# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE status = 'approved'")
    jobs = cursor.fetchall()
    
    if not jobs:
        console.print("[yellow]No approved jobs waiting. (Run src/filter_jobs.py first?)[/yellow]")
        return

    try:
        resume_tpl = get_template("resume.tex")
        cover_tpl = get_template("cover.tex")
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        return

    for job in jobs:
        console.print(f"\n[bold cyan]🤖 Processing: {job['company']} - {job['title']}[/bold cyan]")
        
        # --- CHECK IF ALREADY EXISTS ---
        safe_title = re.sub(r'[^\w\-_]', '_', f"{job['company']}_{job['title']}")
        folder_path = os.path.join(OUTPUT_DIR, safe_title)
        
        resume_path = os.path.join(folder_path, "resume.tex")
        cover_path = os.path.join(folder_path, "cover.tex")

        # If both files exist, skip this job
        if os.path.exists(resume_path) and os.path.exists(cover_path):
            console.print(f"[dim]   ⏭️  Already generated in {folder_path}. Skipping.[/dim]")
            continue

        # --- PHASE 1: DRAFTING ---
        prompt_draft = f"""
TASK:
Generate a tailored LaTeX resume AND LaTeX cover letter for the following job posting.

OUTPUT REQUIREMENTS:
1. Output TWO separate LaTeX documents:
   - Resume (.tex)
   - Cover Letter (.tex)
2. Use the moderncv class exactly as in the templates
3. Keep content ATS-friendly: No tables, No icons.
4. Adapt wording to match the job posting.
5. Emphasize technical, pipeline, automation, and graphics relevance.

JOB POSTING:
{job['description'][:3500]}

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

LATEX RESUME TEMPLATE:
{resume_tpl}

LATEX COVER LETTER TEMPLATE:
{cover_tpl}

FINAL OUTPUT FORMAT:
=== RESUME ===
<LaTeX code>
=== COVER LETTER ===
<LaTeX code>
"""
        console.print("   ↳ 1/2 Drafting content...")
        response_draft, context = call_ollama(prompt_draft)
        
        # If timeout or error occurred, skip to next job
        if not response_draft: 
            console.print("[yellow]   ⚠️  Skipping due to error/timeout.[/yellow]")
            continue

        # --- PHASE 2: VERIFICATION ---
        prompt_verify = """
Review the generated resume and cover letter.
Check for hallucinations, formatting errors, and ensure placeholders are filled.
Output fixed LaTeX:

=== RESUME ===
...
=== COVER LETTER ===
...
"""
        console.print("   ↳ 2/2  Verifying & Polishing...")
        response_final, _ = call_ollama(prompt_verify, context=context)
        
        if not response_final:
             console.print("[yellow]   ⚠️  Skipping verification due to error/timeout.[/yellow]")
             continue

        # --- PHASE 3: SAVING ---
        resume, cover = extract_code_blocks(response_final)
        
        if resume and cover:
            os.makedirs(folder_path, exist_ok=True)
            
            with open(resume_path, "w") as f:
                f.write(resume)
            with open(cover_path, "w") as f:
                f.write(cover)
                
            console.print(f"[green]   ✅ Saved to: {folder_path}[/green]")
            
            cursor.execute("UPDATE jobs SET status = 'generated' WHERE id = ?", (job['id'],))
            conn.commit()
        else:
            console.print("[red]   ❌ Could not parse AI output. Skipping.[/red]")

    conn.close()
    console.print("\n[bold green]✨ Generation complete![/bold green]")

if __name__ == "__main__":
    run()
