import sqlite3
import os
import requests
import json
import re
from rich.console import Console
from jinja2 import Environment, FileSystemLoader

console = Console()

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

DB_PATH = "data/db/jobs.db"
TEMPLATE_DIR = "data/templates"
OUTPUT_DIR = "data/applications"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"
TIMEOUT_SECONDS = 200

# -----------------------------------------------------------------------------
# CANDIDATE PROFILE (LLM INPUT ONLY)
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
  - Python automation of production workflows
  - Vendor and outsourcing coordination
  - Data modeling and reporting (Power BI)
  - Pipeline integration support (Meshroom)
  - Liaison between artists and technical teams

Technical Skills:
- Python, C++
- OpenGL, Vulkan
- Linux / UNIX
- Git, Maya
"""

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def escape_tex(text: str) -> str:
    if not isinstance(text, str):
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    regex = re.compile("|".join(re.escape(k) for k in replacements))
    return regex.sub(lambda m: replacements[m.group()], text)

def normalize_cover_letter_body(value) -> str:
    """
    Ollama may return:
    - string
    - list[str]
    - dict { paragraphs: [...] }
    Normalize ALL into a single string with double newlines.
    """
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "\n\n".join(str(p).strip() for p in value)

    if isinstance(value, dict):
        if "paragraphs" in value and isinstance(value["paragraphs"], list):
            return "\n\n".join(str(p).strip() for p in value["paragraphs"])

    return ""

def call_ollama(prompt: str) -> dict | None:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
        }
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        raw = r.json()["response"]
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end + 1])
    except Exception as e:
        console.print(f"[red]❌ Ollama failure: {e}[/red]")
        return None

def detect_country(job):
    text = f"{job['location']} {job['description']}".lower()
    if any(k in text for k in ["france", "paris", "lyon"]):
        return "FR"
    if any(k in text for k in ["sweden", "stockholm", "gothenburg", "malmo"]):
        return "SE"
    return "INT"

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def run():
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
        autoescape=False
    )

    resume_tpl = env.get_template("resume.jinja")
    cover_tpl = env.get_template("cover.jinja")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE status='approved'")
    jobs = cur.fetchall()

    if not jobs:
        console.print("[yellow]No approved jobs found.[/yellow]")
        return

    for job in jobs:
        console.print(f"[cyan]🤖 {job['company']} – {job['title']}[/cyan]")

        lang = "FR" if detect_country(job) == "FR" else "EN"

        prompt = f"""
You are a professional recruiter and ATS resume writer.

LANGUAGE: {"FRENCH" if lang == "FR" else "ENGLISH"}

JOB DESCRIPTION:
{job['description'][:2500]}

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

RETURN PURE JSON ONLY:
{{
  "job_title_target": "{job['title']}",
  "profile_summary": "2 sentences, first person",
  "experience_bullets": ["...", "...", "...", "..."],
  "cover_letter_body": "3 paragraphs separated by double newlines"
}}
"""

        data = call_ollama(prompt)
        if not data:
            continue

        # ------------------------------------------------------------------
        # NORMALIZE AI OUTPUT
        # ------------------------------------------------------------------

        data.setdefault("experience_bullets", [])
        raw_cover = data.get("cover_letter_body", "")
        cover_text = normalize_cover_letter_body(raw_cover)

        # ------------------------------------------------------------------
        # IDENTITY (NEVER AI-GENERATED)
        # ------------------------------------------------------------------

        data.update({
            "first_name": "Hugo",
            "last_name": "Schenegg",
            "location": "Paris, France",
            "phone": "+33 6 95 16 42 87",
            "email": "schenegg.hugo@gmail.com",
            "linkedin": "schenegghugo",
            "company_name": job["company"],
            "languages_string": (
                "Français (natif) — Anglais (courant)"
                if lang == "FR"
                else "French (Native) — English (Fluent)"
            ),
            "cl_opening": "Madame, Monsieur," if lang == "FR" else "Dear Hiring Manager,",
            "cl_closing": "Cordialement," if lang == "FR" else "Sincerely,",
            "dates_current": "Jan 2022 – Present",
            "role_current": "Studio Coordinator",
            "company_current": "MPC Paris",
            "location_current": "Paris, France",
            "skills_dict": {
                "Scripting": "Python, C++, Bash",
                "Graphics": "OpenGL, Vulkan, Rendering Pipelines",
                "Tools": "Git, Linux, Maya",
            }
        })

        headers = {
            "FR": {
                "h_profile": "Profil",
                "h_skills": "Compétences techniques",
                "h_experience": "Expérience professionnelle",
                "h_projects": "Projets",
                "h_education": "Formation",
                "h_attributes": "Compétences humaines",
            },
            "EN": {
                "h_profile": "Profile",
                "h_skills": "Technical Skills",
                "h_experience": "Experience",
                "h_projects": "Projects",
                "h_education": "Education",
                "h_attributes": "Attributes",
            }
        }

        data.update(headers[lang])

        # ------------------------------------------------------------------
        # LATEX SANITIZATION
        # ------------------------------------------------------------------

        for k, v in data.items():
            if isinstance(v, str):
                data[k] = escape_tex(v.strip())
            elif isinstance(v, list):
                data[k] = [escape_tex(x) for x in v]

        data["cover_letter_body"] = escape_tex(cover_text)

        # ------------------------------------------------------------------
        # RENDER
        # ------------------------------------------------------------------

        folder = re.sub(r"[^\w\-]+", "_", f"{job['company']}_{job['title']}")
        out_dir = os.path.join(OUTPUT_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)

        with open(os.path.join(out_dir, "resume.tex"), "w") as f:
            f.write(resume_tpl.render(data))

        with open(os.path.join(out_dir, "cover.tex"), "w") as f:
            f.write(cover_tpl.render(data))

        cur.execute("UPDATE jobs SET status='generated' WHERE id=?", (job["id"],))
        conn.commit()

        console.print(f"[green]✅ Generated: {out_dir}[/green]")

    conn.close()
    console.print("\n[bold green]✨ Generation complete.[/bold green]")

if __name__ == "__main__":
    run()

