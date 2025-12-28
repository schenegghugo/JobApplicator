#!/usr/bin/env bash
set -e

echo "======================================================"
echo " ATS Job Automation – Setup Script (Arch Linux Edition)"
echo " Strategy: Direct-to-Source (Teamtailor / ATS)"
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
  texlive-xetex \
  texlive-fontsrecommended

echo "✅ System dependencies installed"

# -----------------------------
# 2. Project structure
# -----------------------------
echo "📁 Creating project structure..."

mkdir -p \
  src/{scrapers/parsers,normalizers,scoring,latex,redactor,utils} \
  data/{raw_jobs,db} \
  resumes/{canonical,variants} \
  cover_letters/{templates,generated} \
  templates/latex \
  config \
  logs \
  scripts \
  tests

# Creating init files and the parser placeholders including the new Teamtailor one
touch \
  src/__init__.py \
  src/scrapers/__init__.py \
  src/scrapers/parsers/__init__.py \
  src/scrapers/parsers/{greenhouse.py,lever.py,ashby.py,teamtailor.py} \
  src/redactor/__init__.py \
  src/utils/__init__.py

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

pip install \
  requests \
  beautifulsoup4 \
  lxml \
  playwright \
  pyyaml \
  jinja2 \
  python-dotenv \
  sqlalchemy \
  rich \
  tqdm \
  spacy \
  pydantic \
  langdetect \
  regex \
  click

echo "📥 Installing Playwright Chromium..."
playwright install chromium

# -----------------------------
# 5. spaCy language model
# -----------------------------
echo "🧠 Installing spaCy language model..."
python -m spacy download en_core_web_sm

# -----------------------------
# 6. Environment variables
# -----------------------------
echo "🔐 Creating .env template..."

cat <<EOF > .env
# ============================================
# ATS Job Automation – Environment
# ============================================

PROJECT_ENV=development
LOG_LEVEL=INFO

# Scraping behavior
SCRAPE_INTERVAL_HOURS=6
# Generic User Agent to avoid Cloudflare blocks
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36

# Paths
DATABASE_PATH=data/db/jobs.db
LOG_PATH=logs/
EOF

# -----------------------------
# 7. Git hygiene
# -----------------------------
echo "🧹 Creating .gitignore..."

cat <<EOF > .gitignore
# Python
.venv/
__pycache__/
*.pyc

# Environment
.env

# Data & logs
data/
logs/

# PDFs
*.pdf

# Playwright
.playwright/

# OS
.DS_Store
EOF

# -----------------------------
# 8. Core configuration
# -----------------------------
echo "⚙️ Creating configuration files..."

cat <<EOF > config/targets.yaml
# ============================================
# ATS Targets (Nordic / Game Dev Focus)
# ============================================

teamtailor:
  - https://career.paradoxplaza.com/jobs
  - https://careers.avalanchestudios.com/jobs
  - https://career.embark-studios.com/jobs
  - https://jobs.fatsharkgames.com/jobs
  - https://jobs.machinegames.com/jobs
  - https://jobs.stunlock.com/jobs
  - https://jobs.frictionalgames.com/jobs
  - https://jobs.coffeestain.se/jobs
  - https://jobs.tarsier.se/jobs
  - https://jobs.starbreeze.com/jobs
  - https://jobs.arrowheadgamestudios.com/jobs
  - https://career.snowprintstudios.com/jobs
  - https://jobs.neongiant.se/jobs
  - https://jobs.mightanddelight.com/jobs
  - https://career.goodbyekansas.com/jobs
  - https://career.chimneygroup.com/jobs

custom:
  # Add custom parsers later for these
  # - https://www.ea.com/careers
  # - https://careers.king.com/

roles:
  include:
    - Engineer
    - Developer
    - Programmer
    - Technical Artist
  soft_exclude:
    - Manager
    - Director
    - Lead
    - Intern
EOF

cat <<EOF > config/keywords.yaml
skills:
  graphics:
    - Vulkan
    - OpenGL
    - DirectX
    - HLSL
    - GLSL
    - Rendering
    - Shaders
  engine:
    - Unreal
    - Unity
    - Godot
    - C++
  general:
    - Python
    - Git
    - CI/CD
    - Docker
EOF

# -----------------------------
# 9. Canonical resume schema
# -----------------------------
echo "📄 Creating canonical resume template..."

cat <<EOF > resumes/canonical/resume.yaml
personal:
  name: "Hugo Developer"
  title: "Game Engine Programmer"
  email: "hugo@example.com"
  location: "Stockholm, Sweden"
  linkedin: "linkedin.com/in/hugo"
  nationality: "EU Citizen"

summary: >
  Experienced Engine Programmer...

skills:
  - category: Graphics
    items: []
  - category: Engine
    items: []

experience:
  - company: ""
    role: ""
    start: ""
    end: ""
    bullets:
      - ""

education:
  - degree: ""
    institution: ""
    year: ""
EOF

# -----------------------------
# 10. Database bootstrap
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
  language TEXT,
  date_scraped DATETIME DEFAULT CURRENT_TIMESTAMP,
  status TEXT DEFAULT 'new'
);
EOF

# -----------------------------
# 11. Sanity checks
# -----------------------------
echo "🔍 Running sanity checks..."

python - <<EOF
import spacy, langdetect, pydantic, jinja2
print("Python deps OK")
EOF

# Check for xelatex specifically as it handles fonts better than pdflatex
xelatex --version >/dev/null && echo "XeLaTeX OK"

echo "======================================================"
echo "✅ ATS Job Automation setup COMPLETE (Arch Version)"
echo "======================================================"
