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
MODEL_NAME = "llama3"

# -----------------------------------------------------------------------------
# CANDIDATE PROFILE (The Ground Truth)
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
    """Sends a request to the local AI model."""
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "context": context, 
        "options": {
            "num_ctx": 8192, # Large context window for long job descriptions
            "temperature": 0.7 # Slight creativity, but mostly deterministic
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=data)
        response.raise_for_status()
        json_resp = response.json()
        return json_resp['response'], json_resp.get('context')
    except Exception as e:
        console.print(f"[bold red]❌ Connection Error: {e}[/bold red]")
        console.print("Make sure Ollama is running: [bold]sudo systemctl start ollama[/bold]")
        return None, None

def extract_code_blocks(text):
    """
    Robustly extracts the Resume and Cover Letter from the AI response.
    It ignores chatty intros and looks specifically for LaTeX structure.
    """
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
        """Finds content between \documentclass and \end{document}"""
        # Look for the start of the document
        start_match = re.search(r"\\documentclass", raw_text)
        # Look for the end of the document
        end_match = re.search(r"\\end\{document\}", raw_text)
        
        if start_match and end_match:
            # Extract exactly the valid block
            return raw_text[start_match.start() : end_match.end()]
        return None
    
    resume_clean = extract_latex(raw_resume)
    cover_clean = extract_latex(raw_cover)
    
    return resume_clean, cover_clean
# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def run():
    # 1. Connect to Database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 2. Fetch APPROVED jobs (Filtered by filter_jobs.py)
    cursor.execute("SELECT * FROM jobs WHERE status = 'approved'")
    jobs = cursor.fetchall()
    
    if not jobs:
        console.print("[yellow]No approved jobs waiting. (Run src/filter_jobs.py first?)[/yellow]")
        return

    # 3. Load Templates
    try:
        resume_tpl = get_template("resume.tex")
        cover_tpl = get_template("cover.tex")
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        return

    # 4. Process Each Job
    for job in jobs:
        console.print(f"\n[bold cyan]🤖 Processing: {job['company']} - {job['title']}[/bold cyan]")
        
        # --- PHASE 1: DRAFTING ---
        prompt_draft = f"""
TASK:
Generate a tailored LaTeX resume AND LaTeX cover letter for the following job posting,
using the provided LaTeX templates and candidate profile.

OUTPUT REQUIREMENTS:
1. Output TWO separate LaTeX documents:
   - Resume (.tex)
   - Cover Letter (.tex)
2. Use the moderncv class exactly as in the templates
3. Keep content ATS-friendly: No tables, No icons, Clear keywords.
4. Adapt wording to match the job posting.
5. Emphasize technical, pipeline, automation, and graphics relevance.
6. Do NOT exaggerate or fabricate experience.
7. Use concise, professional VFX/Game industry language.

––––––––––––––––––––
JOB POSTING (RAW TEXT):
{job['description'][:3500]}

––––––––––––––––––––
CANDIDATE PROFILE (GROUND TRUTH — DO NOT INVENT):
{CANDIDATE_PROFILE}

––––––––––––––––––––
LATEX RESUME TEMPLATE (DO NOT CHANGE STRUCTURE):
{resume_tpl}

––––––––––––––––––––
LATEX COVER LETTER TEMPLATE (DO NOT CHANGE STRUCTURE):
{cover_tpl}

––––––––––––––––––––
ADAPTATION RULES:
- Mirror terminology from the job description when truthful.
- Prioritize Python, automation, pipeline support, and graphics foundations.
- If the role is Games-focused, emphasize real-time graphics and tools.
- If the role is VFX-focused, emphasize pipeline, data, and production support.
- Keep resume to 1 page when possible.

––––––––––––––––––––
FINAL OUTPUT FORMAT:

=== RESUME ===
<LaTeX code>

=== COVER LETTER ===
<LaTeX code>
"""
        console.print("   ↳ 🧠 Drafting content...")
        response_draft, context = call_ollama(prompt_draft)
        if not response_draft: continue

        # --- PHASE 2: VERIFICATION ---
        prompt_verify = """
Review the generated resume and cover letter.

Check for:
1. Invented tools or skills (Hallucinations).
2. Overclaiming seniority.
3. Buzzwords without evidence.
4. ATS-breaking formatting.
5. LaTeX compilation errors (ensure % and & are escaped like \% \&).
6. Ensure placeholders like [COMPANY_NAME] in the cover letter are filled with the real company name.

If issues exist:
- Correct them.
- Output the fixed LaTeX in the same format:

=== RESUME ===
...
=== COVER LETTER ===
...
"""
        console.print("   ↳ 🕵️  Verifying & Polishing...")
        response_final, _ = call_ollama(prompt_verify, context=context)

        # --- PHASE 3: SAVING ---
        resume, cover = extract_code_blocks(response_final)
        
        if resume and cover:
            # Create a safe folder name (e.g., "MPC_Pipeline_TD")
            safe_title = re.sub(r'[^\w\-_]', '_', f"{job['company']}_{job['title']}")
            folder_path = os.path.join(OUTPUT_DIR, safe_title)
            os.makedirs(folder_path, exist_ok=True)
            
            # Write files
            with open(os.path.join(folder_path, "resume.tex"), "w") as f:
                f.write(resume)
            with open(os.path.join(folder_path, "cover.tex"), "w") as f:
                f.write(cover)
                
            console.print(f"[green]   ✅ Saved to: {folder_path}[/green]")
            
            # Mark as done in DB
            cursor.execute("UPDATE jobs SET status = 'generated' WHERE id = ?", (job['id'],))
            conn.commit()
        else:
            console.print("[red]   ❌ Could not parse AI output. Skipping.[/red]")

    conn.close()
    console.print("\n[bold green]✨ Generation complete![/bold green]")

if __name__ == "__main__":
    run()
