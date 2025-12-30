import sqlite3
import os
import requests
import json
import re
from rich.console import Console
from jinja2 import Environment, FileSystemLoader

console = Console()

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

DB_PATH = "data/db/jobs.db"
TEMPLATE_DIR = "data/templates"
OUTPUT_DIR = "data/applications"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"
TIMEOUT_SECONDS = 200

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
"""

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def call_ollama_json(prompt):
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.2
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        console.print(f"[bold red]❌ Ollama Error: {e}[/bold red]")
        return None

def clean_json_string(json_str):
    if not json_str: return ""
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end != -1:
        return json_str[start:end+1]
    return json_str

def escape_tex(text):
    """
    Robustly escapes LaTeX special characters.
    """
    if not isinstance(text, str): return text
    
    chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    
    regex = re.compile('|'.join(re.escape(key) for key in chars.keys()))
    return regex.sub(lambda m: chars[m.group()], text)

def check_if_sweden(job):
    """Checks if the job is located in Sweden."""
    text = (job['location'] + " " + job['description']).lower()
    return any(x in text for x in ["sweden", "stockholm", "malmö", "malmo", "gothenburg"])

# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def run():
    if not os.path.exists(TEMPLATE_DIR):
        console.print(f"[red]❌ Template directory not found: {TEMPLATE_DIR}[/red]")
        return
    
    # Use LaTeX-safe delimiters
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>'
    )
    
    try:
        resume_template = env.get_template("resume.jinja")
        cover_template = env.get_template("cover.jinja")
    except Exception as e:
        console.print(f"[bold red]❌ Template Error: {e}[/bold red]")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE status = 'approved'")
    jobs = cursor.fetchall()
    
    if not jobs:
        console.print("[yellow]No approved jobs waiting.[/yellow]")
        return

    for job in jobs:
        console.print(f"\n[bold cyan]🤖 Processing: {job['company']} - {job['title']}[/bold cyan]")
        
        safe_title = re.sub(r'[^\w\-_]', '_', f"{job['company']}_{job['title']}")
        folder_path = os.path.join(OUTPUT_DIR, safe_title)
        
        resume_path = os.path.join(folder_path, "resume.tex")
        cover_path = os.path.join(folder_path, "cover.tex")

        # --- DYNAMIC SWEDEN LOGIC ---
        is_sweden = check_if_sweden(job)
        sweden_instruction = ""
        if is_sweden:
            console.print("   🇸🇪 Sweden detected! Adding relocation logic.")
            sweden_instruction = """
            CRITICAL SWEDEN INSTRUCTION:
            - This job is in Sweden. You MUST add a specific paragraph in the cover letter body.
            - State clearly: "My main motivation for relocating to Scandinavia is to be closer to my spouse's family."
            - Mention that I speak conversational Swedish.
            """

        prompt = f"""
You are an expert career coach and technical writer.
Analyze the JOB DESCRIPTION and CANDIDATE PROFILE below.
Write a highly customized resume summary and cover letter.

JOB DESCRIPTION:
{job['description'][:2500]}

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

INSTRUCTIONS:
1. "job_title_target": Use the exact job title from the listing.
2. "profile_summary": Write 2 strong sentences in the FIRST PERSON ("I am...", "I have..."). Do NOT use third person ("Hugo is...").
3. "mpc_bullets": Rewrite 4 specific bullet points from the candidate's MPC experience. Ensure they are relevant to the job.
4. "skills_graphics": If the job mentions graphics/rendering, list "OpenGL, Vulkan, Rendering Pipelines". If not, list them anyway as they are core skills.
5. "cover_letter_body": Write the BODY ONLY.
   - Do NOT include "Dear Hiring Manager" (the template handles this).
   - Do NOT include "Sincerely" or the signature (the template handles this).
   - Paragraph 1: Enthusiastic intro mentioning the role.
   - Paragraph 2: Connect Python/C++ skills to the requirements.
   - Paragraph 3: Professional closing.
   - USE DOUBLE NEWLINES (\\n\\n) between paragraphs.
   {sweden_instruction}

OUTPUT FORMAT (Pure JSON only):
{{
  "company_name": "{job['company']}",
  "job_title": "{job['title']}",
  "job_title_target": "...",
  "profile_summary": "I am a...",
  "skills_scripting": "Python, C++, Bash",
  "skills_software": "Maya, Linux, Git",
  "skills_graphics": "OpenGL, Vulkan, Rendering Pipelines",
  "mpc_bullets": [
    "Implemented...",
    "Developed...",
    "Coordinated...",
    "Automated..."
  ],
  "cover_letter_body": "..."
}}
"""
        console.print("   ↳ 🧠 Generating structured data...")
        raw_json = call_ollama_json(prompt)
        
        if not raw_json: continue

        try:
            clean_str = clean_json_string(raw_json)
            data = json.loads(clean_str)

            # --- DATA CLEANUP & FALLBACKS ---

            # 1. Force Graphics Skills if empty
            if not data.get("skills_graphics") or len(data["skills_graphics"]) < 3:
                data["skills_graphics"] = "OpenGL, Vulkan, Rendering Pipelines"

            # 2. Fix Cover Letter Paragraphs & Remove Greeting/Signoff
            if "cover_letter_body" in data:
                body = data["cover_letter_body"]
                # Remove common duplications if the AI ignored instructions
                body = re.sub(r"Dear.*?Manager,?", "", body, flags=re.IGNORECASE)
                body = re.sub(r"Sincerely,?", "", body, flags=re.IGNORECASE)
                body = re.sub(r"Hugo Schenegg", "", body, flags=re.IGNORECASE)
                
                # Ensure Double Newlines
                if "\n\n" not in body:
                    body = body.replace("\n", "\n\n")
                
                data["cover_letter_body"] = escape_tex(body.strip())

            # 3. Clean Bullets (Remove leading dashes)
            if "mpc_bullets" in data and isinstance(data["mpc_bullets"], list):
                cleaned_bullets = []
                for b in data["mpc_bullets"]:
                    # Remove leading "- " or "* " and whitespace
                    clean_b = re.sub(r"^[\-\*]\s*", "", b).strip()
                    cleaned_bullets.append(clean_b)
                data["mpc_bullets"] = cleaned_bullets

            # --- ESCAPING FOR LATEX ---
            for key, value in data.items():
                if key == "cover_letter_body": continue # Already handled
                if isinstance(value, str):
                    data[key] = escape_tex(value)
                elif isinstance(value, list):
                    data[key] = [escape_tex(v).replace("\n", " ") for v in value]

            # Render
            resume_content = resume_template.render(data)
            cover_content = cover_template.render(data)
            
            os.makedirs(folder_path, exist_ok=True)
            with open(resume_path, "w") as f: f.write(resume_content)
            with open(cover_path, "w") as f: f.write(cover_content)
            
            console.print(f"[green]   ✅ Generated LaTeX in: {folder_path}[/green]")
            
            cursor.execute("UPDATE jobs SET status = 'generated' WHERE id = ?", (job['id'],))
            conn.commit()
            
        except Exception as e:
            console.print(f"[red]   ❌ Processing Error: {e}[/red]")

    conn.close()
    console.print("\n[bold green]✨ Generation complete![/bold green]")

if __name__ == "__main__":
    run()
