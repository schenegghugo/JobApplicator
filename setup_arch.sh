#!/usr/bin/env bash
set -e

echo "======================================================"
echo " JobApplicator – Setup Script (Arch Linux Edition)"
echo " Strategy: Unified Parser / Local LLM / LaTeX"
echo "======================================================"

# -----------------------------
# 0. Safety checks
# -----------------------------
if [[ "$EUID" -eq 0 ]]; then
  echo "❌ Do NOT run this script as root (sudo is invoked inside only when needed)."
  exit 1
fi

command -v python >/dev/null 2>&1 || {
  echo "❌ Python not found. (On Arch, 'python' is Python 3)."
  exit 1
}

# -----------------------------
# 1. System dependencies (Arch Linux)
# -----------------------------
echo "📦 Installing system dependencies via pacman..."

# Arch specific package mapping
# - texlive-basic/latexextra: For compiling the CVs
# - poppler: For converting/handling PDF data if needed
sudo pacman -Syu --needed --noconfirm \
  base-devel \
  git \
  curl \
  wget \
  sqlite \
  poppler \
  python \
  python-pip \
  texlive-basic \
  texlive-latexextra \
  texlive-fontsrecommended

echo "✅ System dependencies installed"

# -----------------------------
# 2. Project structure
# -----------------------------
echo "📁 Creating project structure..."

# The New Architecture
mkdir -p \
  src/{scrapers,utils} \
  data/{applications,db,raw_jobs,templates} \
  config \
  logs

# Creating empty python modules
touch \
  src/__init__.py \
  src/scrapers/__init__.py \
  src/utils/__init__.py

# Create the core script placeholders
touch \
  src/run_scraper.py \
  src/scrape_details.py \
  src/generate_application.py \
  src/compile_pdfs.py \
  src/scrapers/dispatcher.py \
  src/scrapers/unified_parser.py

echo "✅ Project folders created"

# -----------------------------
# 3. Python virtual environment
# -----------------------------
echo "🐍 Creating Python virtual environment..."

python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip wheel setuptools

# -----------------------------
# 4. Python dependencies
# -----------------------------
echo "📚 Installing Python dependencies..."

# We removed spaCy/langdetect (using Ollama now)
# Added rich (for UI) and PyYAML/Jinja2 (for config/templating)
pip install \
  requests \
  beautifulsoup4 \
  lxml \
  playwright \
  pyyaml \
  jinja2 \
  rich \
  pydantic

echo "📥 Installing Playwright Chromium..."
playwright install chromium

# -----------------------------
# 5. Environment variables
# -----------------------------
echo "🔐 Creating .env template..."

cat <<EOF > .env
# ============================================
# JobApplicator – Environment
# ============================================
PROJECT_ENV=development
LOG_LEVEL=INFO
DATABASE_PATH=data/db/jobs.db
EOF

# -----------------------------
# 6. Git hygiene
# -----------------------------
echo "🧹 Creating .gitignore..."

cat <<EOF > .gitignore
# Python
.venv/
__pycache__/
*.pyc

# Data (Don't commit personal data or large crawls)
data/db/*.db
data/raw_jobs/*.html
data/applications/
logs/

# Env
.env
.DS_Store
EOF

# -----------------------------
# 7. Core configuration
# -----------------------------
echo "⚙️ Creating configuration files..."

# targets.yaml - The list of URLS to scrape
cat <<EOF > config/targets.yaml
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
EOF

# candidate_profile.py - Your personal data for the LLM
cat <<EOF > config/candidate_profile.py
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
EOF

# -----------------------------
# 8. Templates (LaTeX + Jinja)
# -----------------------------
echo "📄 Creating LaTeX templates..."

# resume.jinja - Note the << >> syntax for Jinja to avoid LaTeX conflicts
cat <<EOF > data/templates/resume.jinja
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
EOF

# -----------------------------
# 9. Database bootstrap
# -----------------------------
echo "🗄️ Initializing SQLite database..."

sqlite3 data/db/jobs.db <<EOF
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  company TEXT,
  ats_provider TEXT,
  title TEXT,
  location TEXT,
  apply_url TEXT,
  description TEXT,
  status TEXT DEFAULT 'new', -- new, approved, applied, ignored
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
EOF

# -----------------------------
# 10. Sanity checks
# -----------------------------
echo "🔍 Running sanity checks..."

python - <<EOF
import yaml, jinja2, rich, playwright
print("✅ Python dependencies loaded successfully.")
EOF

# Check for pdflatex
pdflatex --version >/dev/null && echo "✅ pdfLaTeX detected." || echo "⚠️ pdfLaTeX not found. You need it to compile PDFs."

echo "======================================================"
echo "✨ JobApplicator Setup Complete!"
echo "   1. Activate venv: source .venv/bin/activate"
echo "   2. Scrape jobs:   python src/run_scraper.py"
echo "======================================================"
