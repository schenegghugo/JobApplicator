import sys
import sqlite3
import os
import requests
import json
import re
import argparse
import copy
from rich.console import Console
from jinja2 import Environment, FileSystemLoader

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.logic.loader import load_profile
from src.logic.hooks import process_hooks
from src.utils.paths import get_profile_paths

console = Console()

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

OUTPUT_DIR = "data/applications" 
TEMPLATE_DIR = "data/templates"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"
TIMEOUT_SECONDS = 1200 

UI_TRANSLATIONS = {
    "en": { 
        "h_profile": "Summary", 
        "h_experience": "Experience", 
        "h_education": "Education", 
        "h_skills": "Technical Skills",
        "h_projects": "Key Projects",
        "h_attributes": "Attributes",
        "cl_opening": "Dear Hiring Manager,",
        "cl_closing": "Sincerely,"
    },
    "fr": { 
        "h_profile": "Résumé", 
        "h_experience": "Expérience Professionnelle", 
        "h_education": "Formation", 
        "h_skills": "Compétences Techniques",
        "h_projects": "Projets Clés",
        "h_attributes": "Savoir-être",
        "cl_opening": "Madame, Monsieur,",
        "cl_closing": "Cordialement,"
    }
}

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def call_ollama_json(prompt):
    data = {
        "model": MODEL_NAME, "prompt": prompt, "format": "json", "stream": False,
        "options": { "num_ctx": 4096, "temperature": 0.2 }
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
    if start != -1 and end != -1: return json_str[start:end+1]
    return json_str

def escape_tex_string(text):
    if not isinstance(text, str): return str(text)
    chars = { 
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", 
        "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", 
        "\\": r"\textbackslash{}"
    }
    regex = re.compile('|'.join(re.escape(key) for key in chars.keys()))
    return regex.sub(lambda m: chars[m.group()], text)

def recursive_escape(data):
    if isinstance(data, dict):
        return {k: recursive_escape(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_escape(i) for i in data]
    elif isinstance(data, str):
        return escape_tex_string(data)
    elif isinstance(data, (int, float, bool)):
        return str(data)
    elif data is None:
        return ""
    else:
        return str(data)

def to_dict(obj):
    if hasattr(obj, 'model_dump'): return obj.model_dump()
    if hasattr(obj, 'dict'): return obj.dict()
    if isinstance(obj, dict): return obj
    return obj

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def run(profile_name):
    console.print(f"[bold blue]👤 Loading Profile: {profile_name}[/bold blue]")
    
    paths = get_profile_paths(profile_name)
    db_path = paths['db_file']
    output_base_dir = os.path.join(OUTPUT_DIR, profile_name)

    # Load Data
    try:
        raw_data = load_profile(profile_name)
        if len(raw_data) == 2: identity_obj, strategy_obj = raw_data
        elif len(raw_data) >= 3: identity_obj, strategy_obj = raw_data[0], raw_data[1]
        else: raise ValueError("Invalid profile data")

        identity = to_dict(identity_obj)
        strategy_dict = to_dict(strategy_obj)
        
    except Exception as e:
        console.print(f"[bold red]❌ Profile Load Error: {e}[/bold red]")
        return

    # Setup Jinja
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string='<%', block_end_string='%>',
        variable_start_string='<<', variable_end_string='>>',
        comment_start_string='<#', comment_end_string='#>'
    )
    try:
        resume_template = env.get_template("resume.jinja")
        cover_template = env.get_template("cover.jinja")
    except Exception as e:
        console.print(f"[bold red]❌ Jinja Error: {e}[/bold red]")
        return

    # DB Connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE status = 'approved'")
    jobs = cursor.fetchall()
    
    if not jobs:
        console.print(f"[yellow]⚠️ No approved jobs found.[/yellow]")
        return

    console.print(f"[bold green]🚀 Found {len(jobs)} jobs.[/bold green]")

    for job in jobs:
        console.print(f"\n[bold cyan]🤖 Processing: {job['company']}[/bold cyan]")
        
        safe_title = re.sub(r'[^\w\-_]', '_', f"{job['id']}_{job['company']}_{job['title']}")[:50]
        folder_path = os.path.join(output_base_dir, safe_title)
        
        # --- PREPARE BASE DATA ---
        final_data = copy.deepcopy(identity)
        if 'basics' in final_data:
            final_data.update(final_data['basics'])

        full_name = final_data.get('name', 'Candidate Name').split(" ")
        final_data['first_name'] = full_name[0]
        final_data['last_name'] = " ".join(full_name[1:]) if len(full_name) > 1 else ""
        final_data['company_name'] = job['company']
        
        # FIX: Robust Language Extraction
        langs = final_data.get('languages', [])
        if langs:
            clean_langs = []
            for l in langs:
                if isinstance(l, str): clean_langs.append(l)
                elif isinstance(l, dict) and 'language' in l: clean_langs.append(l['language'])
            final_data['languages_string'] = " -- ".join(clean_langs)
        else:
            final_data['languages_string'] = ""

        # Experience Context
        experiences = final_data.get('experience', [])
        if experiences:
            current_job = experiences[0] 
            final_data['role_current'] = current_job.get('role', 'Role')
            final_data['company_current'] = current_job.get('company', 'Company')
            final_data['dates_current'] = current_job.get('dates', 'Present')
            final_data['location_current'] = current_job.get('location', '')
            final_data['experience_history'] = experiences[1:]
        else:
            final_data['role_current'] = "Professional"
            final_data['company_current'] = ""
            final_data['dates_current'] = ""
            final_data['location_current'] = ""
            final_data['experience_history'] = []

        # --- LLM GENERATION ---
        injections = process_hooks(job['description'], strategy_obj)
        
        target_lang = "en"
        instruction = "Write in English."
        if strategy_dict.get('settings', {}).get('auto_detect_language', True):
            if any(w in job['description'].lower() for w in ["pour", "expérience", "cdi", "cdd"]):
                target_lang = "fr"
                instruction = "Write in FRENCH."

        final_data.update(UI_TRANSLATIONS.get(target_lang, UI_TRANSLATIONS["en"]))

        # PROMPT: Asking for Categorized Skills Dictionary
        prompt = f"""
You are a career expert helping {final_data.get('name')}.
CONTEXT: Target Language: {target_lang.upper()}. {instruction}

JOB: {job['description'][:2000]}
PROFILE: {json.dumps(identity, ensure_ascii=False)}
INJECTIONS: {json.dumps(injections, ensure_ascii=False)}

TASK: Generate JSON.
1. "experience_bullets": 4 bullet points for the most recent role.
2. "profile_summary": 2 lines first person summary.
3. "skills_dict": A dictionary where keys are short categories (e.g. "Languages", "Technical", "Management") and values are comma-separated strings.
4. "cover_letter_body": 3 paragraphs. NO GREETINGS. NO SIGN-OFF.

OUTPUT JSON:
{{
  "job_title_target": "Target Job Title",
  "profile_summary": "...",
  "skills_dict": {{ "Category1": "Skill A, Skill B", "Category2": "Skill C, Skill D" }},
  "experience_bullets": ["...","..."],
  "cover_letter_body": "..."
}}
"""
        console.print(f"   ↳ 🧠 Generating ({target_lang})...")
        raw_json = call_ollama_json(prompt)
        
        if raw_json:
            try:
                llm_data = json.loads(clean_json_string(raw_json))
                final_data.update(llm_data)

                # 1. Clean Bullets
                bullets = final_data.get("experience_bullets", [])
                clean_bullets = []
                if isinstance(bullets, list):
                    for b in bullets:
                        cb = re.sub(r"^[\-\*•]\s*", "", str(b)).strip().replace("\n", " ") 
                        if cb: clean_bullets.append(cb)
                if not clean_bullets: clean_bullets = ["Experience details available upon request."]
                final_data["experience_bullets"] = clean_bullets

                # 2. Clean Cover Letter
                if "cover_letter_body" in final_data:
                    body = final_data["cover_letter_body"]
                    body = re.sub(r"(Dear|Sincerely|Cordialement|Best regards).*?,?", "", body, flags=re.IGNORECASE)
                    body = re.sub(r'\n+', '\n\n', body.strip())
                    if body.endswith(r"\\"): body = body[:-2].strip()
                    final_data["cover_letter_body"] = body

                # 3. ESCAPING
                cl_body = final_data.pop("cover_letter_body", "")
                final_data = recursive_escape(final_data)

                if cl_body:
                    paragraphs = cl_body.split('\n\n')
                    escaped_paragraphs = [escape_tex_string(p.strip()) for p in paragraphs if p.strip()]
                    final_data["cover_letter_body"] = "\n\n".join(escaped_paragraphs)
                else:
                    final_data["cover_letter_body"] = ""

                # Render
                os.makedirs(folder_path, exist_ok=True)
                with open(os.path.join(folder_path, "resume.tex"), "w") as f:
                    f.write(resume_template.render(final_data))
                with open(os.path.join(folder_path, "cover.tex"), "w") as f:
                    f.write(cover_template.render(final_data))

                console.print(f"[green]   ✅ Generated in: {folder_path}[/green]")
                cursor.execute("UPDATE jobs SET status = 'generated' WHERE id = ?", (job['id'],))
                conn.commit()

            except Exception as e:
                console.print(f"[red]   ❌ Error processing JSON: {e}[/red]")
        else:
             console.print(f"[yellow]   ⚠️ Skipped due to Ollama timeout/error[/yellow]")
        
    conn.close()
    console.print("\n[bold green]✨ Generation complete![/bold green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=str, required=True)
    args = parser.parse_args()
    run(args.profile)
