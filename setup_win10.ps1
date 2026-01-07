<#
.SYNOPSIS
    JobApplicator Setup Script (Windows 10/11 Edition)
.DESCRIPTION
    Sets up the Python environment, folder structure, database, and config files.
#>

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " JobApplicator – Setup Script (Windows Edition)"
Write-Host " Strategy: Unified Parser / Local LLM / LaTeX"
Write-Host "======================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# -----------------------------
# 1. System Dependencies Check
# -----------------------------
Write-Host "`n📦 Checking System Dependencies..." -ForegroundColor Yellow

function Check-Command ($cmd, $installHint) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Host "   [OK] Found $cmd" -ForegroundColor Green
    } else {
        Write-Host "   [MISSING] $cmd not found." -ForegroundColor Red
        Write-Host "   -> Install via Winget: $installHint"
        Write-Host "   -> Or download manually."
    }
}

Check-Command "python" "winget install Python.Python.3.11"
Check-Command "git" "winget install Git.Git"
Check-Command "pdflatex" "winget install MiKTeX.MiKTeX" 

# Check for Winget presence to offer auto-install
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "`n   (Tip: If you are missing dependencies, run this script as Admin to attempt install)" -ForegroundColor Gray
}

# -----------------------------
# 2. Project Structure
# -----------------------------
Write-Host "`n📁 Creating project structure..." -ForegroundColor Yellow

$folders = @(
    "src/scrapers",
    "src/utils",
    "data/applications",
    "data/db",
    "data/raw_jobs",
    "data/templates",
    "config",
    "logs"
)

foreach ($f in $folders) {
    if (-not (Test-Path $f)) {
        New-Item -ItemType Directory -Path $f | Out-Null
    }
}

# Create empty init files and placeholders
$files = @(
    "src/__init__.py",
    "src/scrapers/__init__.py",
    "src/utils/__init__.py",
    "src/run_scraper.py",
    "src/scrape_details.py",
    "src/generate_application.py",
    "src/compile_pdfs.py",
    "src/scrapers/dispatcher.py",
    "src/scrapers/unified_parser.py"
)

foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

Write-Host "✅ Project folders created." -ForegroundColor Green

# -----------------------------
# 3. Python Virtual Environment
# -----------------------------
Write-Host "`n🐍 Creating Python virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Activate Venv in current session
$env:VIRTUAL_ENV = "$PWD/.venv"
$env:Path = "$PWD/.venv/Scripts;$env:Path"

Write-Host "   Virtual environment created and active for this session." -ForegroundColor Gray

# -----------------------------
# 4. Python Dependencies
# -----------------------------
Write-Host "`n📚 Installing Python dependencies..." -ForegroundColor Yellow

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install requests beautifulsoup4 lxml playwright pyyaml jinja2 rich pydantic

Write-Host "📥 Installing Playwright Chromium..." -ForegroundColor Cyan
playwright install chromium

# -----------------------------
# 5. Environment Variables
# -----------------------------
Write-Host "`n🔐 Creating .env template..." -ForegroundColor Yellow

$envContent = @"
# ============================================
# JobApplicator – Environment
# ============================================
PROJECT_ENV=development
LOG_LEVEL=INFO
DATABASE_PATH=data/db/jobs.db
"@
Set-Content -Path ".env" -Value $envContent -Encoding UTF8

# -----------------------------
# 6. Git Hygiene
# -----------------------------
Write-Host "`n🧹 Creating .gitignore..." -ForegroundColor Yellow

$gitignore = @"
# Python
.venv/
__pycache__/
*.pyc

# Data
data/db/*.db
data/raw_jobs/*.html
data/applications/
logs/

# Env
.env
.DS_Store
"@
Set-Content -Path ".gitignore" -Value $gitignore -Encoding UTF8

# -----------------------------
# 7. Configuration Files
# -----------------------------
Write-Host "`n⚙️ Creating configuration files..." -ForegroundColor Yellow

# targets.yaml
$targetsYaml = @"
# ============================================
# ATS Targets (Nordic / Game Dev Focus)
# ============================================
game_studios:
  - https://career.paradoxplaza.com/jobs
  - https://careers.avalanchestudios.com/jobs
  - https://career.embark-studios.com/jobs
  - https://jobs.fatsharkgames.com/jobs
  - https://jobs.machinegames.com/jobs
  - https://jobs.stunlock.com/jobs
  - https://jobs.frictionalgames.com/jobs
  - https://jobs.coffeestain.se/jobs
  - https://jobs.starbreeze.com/jobs
  - https://jobs.arrowheadgamestudios.com/jobs
  - https://career.snowprintstudios.com/jobs
  - https://jobs.neongiant.se/jobs
  - https://career.goodbyekansas.com/jobs

tech:
  - https://jobs.spotify.com/jobs
  - https://job-boards.greenhouse.io/klarna
"@
Set-Content -Path "config/targets.yaml" -Value $targetsYaml -Encoding UTF8

# candidate_profile.py
$profilePy = @"
# Your personal details for the AI to use
profile = {
    "name": "Hugo Developer",
    "email": "hugo@example.com",
    "phone": "+46 70 123 45 67",
    "linkedin": "linkedin.com/in/hugo",
    "location": "Stockholm, Sweden",
    "bio": "Senior C++ Engine Programmer with 5 years of experience in Unreal Engine and low-level graphics optimization.",
    "skills": ["C++", "Python", "Vulkan", "DirectX", "Unreal Engine 5", "Multithreading"],
    "experience": [
        "Senior Programmer at GameCorp (2020-Present): Optimized render pipeline.",
        "Junior Dev at IndieStudio (2018-2020): Ported game to Switch."
    ]
}
"@
Set-Content -Path "config/candidate_profile.py" -Value $profilePy -Encoding UTF8

# -----------------------------
# 8. Templates
# -----------------------------
Write-Host "`n📄 Creating LaTeX templates..." -ForegroundColor Yellow

# Using << >> for Jinja
$resumeJinja = @"
\documentclass[11pt,a4paper,sans]{moderncv}
\moderncvstyle{banking}
\moderncvcolor{black}
\usepackage[utf8]{inputenc}
\usepackage[scale=0.75]{geometry}

\name{<< name >>}{}
\title{<< title >>}
\address{<< location >>}
\phone[mobile]{<< phone >>}
\email{<< email >>}

\begin{document}
\makecvtitle

\section{Summary}
<< summary >>

\section{Experience}
\begin{itemize}
% for bullet in experience_bullets
    \item << bullet >>
% endfor
\end{itemize}

\section{Skills}
<< skills_list >>

\end{document}
"@
Set-Content -Path "data/templates/resume.jinja" -Value $resumeJinja -Encoding UTF8

# -----------------------------
# 9. Database Bootstrap
# -----------------------------
Write-Host "`n🗄️ Initializing SQLite database..." -ForegroundColor Yellow

# Use Python to create the DB so we don't need sqlite3.exe installed
$dbScript = @"
import sqlite3
import os

db_path = 'data/db/jobs.db'
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''
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
);
''')
conn.commit()
conn.close()
print('Database created successfully.')
"@

python -c $dbScript

# -----------------------------
# 10. Sanity Checks
# -----------------------------
Write-Host "`n🔍 Running sanity checks..." -ForegroundColor Yellow

$checkScript = @"
import yaml, jinja2, rich, playwright
print('   [OK] Python libraries import successful.')
"@
python -c $checkScript

if (Get-Command pdflatex -ErrorAction SilentlyContinue) {
    Write-Host "   [OK] pdfLaTeX detected." -ForegroundColor Green
} else {
    Write-Host "   [WARNING] pdfLaTeX not found." -ForegroundColor Red
    Write-Host "             You need MiKTeX or TeXLive to compile PDFs."
}

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "✨ JobApplicator Setup Complete!"
Write-Host "   1. Activate venv: .\.venv\Scripts\Activate.ps1"
Write-Host "   2. Scrape jobs:   python src/run_scraper.py"
Write-Host "======================================================" -ForegroundColor Cyan
