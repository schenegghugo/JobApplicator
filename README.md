***

# JobApplicator

**JobApplicator** is a fully automated, local-first pipeline designed to scrape job listings, manage applications, and generate hyper-tailored, professional LaTeX resumes and cover letters using local AI.

## ⚡ Tech Stack

*   **Language:** Python 3.10+
*   **AI Engine:** **Ollama** (Llama 3.2) – *Zero cost, high privacy, runs locally.*
*   **Web Scraping:** **Playwright** + **BeautifulSoup** – *Handles dynamic JS sites & smart parsing.*
*   **Database:** **SQLite** – *Lightweight local storage.*
*   **Templating:** **Jinja2** – *Logic-based content generation.*
*   **Typesetting:** **LaTeX** (ModernCV) – *Industry-standard PDF generation.*
*   **UI/Logging:** **Rich** – *Beautiful terminal output.*

---

## 🔄 The Workflow Pipeline

### 1. Discovery (`src/run_scraper.py`)
*   **Action:** Browses career pages defined in `config/targets.yaml`.
*   **Logic:** Uses a **Smart Dispatcher** to detect the ATS (Greenhouse, Teamtailor, Lever, etc.) and routes the HTML to a **Unified Parser**.
*   **Storage:** Saves new listings into `data/db/jobs.db` with status `new`.

### 2. Extraction (`src/scrape_details.py`)
*   **Action:** Visits the specific job URL for every `new` job found.
*   **Logic:** Downloads the full HTML body and extracts the raw text description.
*   **Output:** Saves raw HTML to `data/raw_jobs/` and updates the DB entry.

### 3. Curation (Manual)
*   **Action:** You review the database (using a SQLite browser or custom script).
*   **Logic:** Change the status of jobs you want to apply for from `new` $\to$ `approved`.

### 4. Generation (`src/generate_application.py`)
*   **Action:** Reads `approved` jobs and your Candidate Profile.
*   **AI Processing:** Sends a strict prompt to **Ollama** requesting **JSON output**:
    *   Summarizes fit for the role (First-person).
    *   Rewrites experience bullets to match the job description keywords.
    *   Writes a custom cover letter body.
*   **Smart Logic:**
    *   **🇸🇪 Sweden Detector:** Injects specific clauses about language skills/family if the location is Swedish.
    *   **LaTeX Safety:** Escapes special characters (`&`, `%`, `_`) to prevent compiler crashes.
    *   **Jinja Templating:** Uses `<< >>` delimiters to avoid conflicts with LaTeX syntax.

### 5. Compilation (`src/compile_pdfs.py`)
*   **Action:** Iterates through generated folders in `data/applications/`.
*   **Logic:** Runs `pdflatex` to transform `.tex` source files into professional PDFs.

---

## 📂 Project Structure

```text
JobApplicator/
├── config/
│   ├── targets.yaml          # List of company URLs to scrape
│   └── candidate_profile.py  # Your skills, experience, and bio
│
├── data/
│   ├── applications/         # Generated PDF folders
│   ├── db/
│   │   └── jobs.db           # SQLite Database
│   ├── raw_jobs/             # Cached HTML files for debugging
│   └── templates/
│       ├── cover.jinja       # LaTeX Cover Letter Template
│       └── resume.jinja      # LaTeX Resume Template
│
├── src/
│   ├── scrapers/
│   │   ├── dispatcher.py     # Detects ATS (Greenhouse/Lever/etc)
│   │   └── unified_parser.py # Centralized parsing logic
│   ├── utils/
│   ├── compile_pdfs.py       # PDF Compiler
│   ├── generate_application.py # AI Generation Logic
│   ├── run_scraper.py        # Main entry point for discovery
│   └── scrape_details.py     # Content fetcher
│
├── main.py                   # Orchestrator
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### 1. Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Run the Pipeline

**Step 1: Find Jobs**
Scrapes target websites and populates the database.
```bash
python src/run_scraper.py
```

**Step 2: Get Details**
Fetches the full description for found jobs.
```bash
python src/scrape_details.py
```

**Step 3: Approve Jobs**
*Open `data/db/jobs.db` using a SQLite viewer and change the `status` column of desired jobs to **'approved'**.*

**Step 4: Generate PDFs**
Uses AI to write the content and creates the folder structure.
```bash
python src/generate_application.py
```

**Step 5: Compile**
Turns the generated `.tex` files into PDFs.
```bash
python src/compile_pdfs.py
```

---

## ✨ Key Features
*   **Unified ATS Parsing:** A single module handles Ashby, Greenhouse, Lever, Teamtailor, Workday, and more.
*   **Resilient Templating:** Solved the conflict between Jinja `{{ }}` and LaTeX `{ }` by using custom `<< >>` delimiters.
*   **Strict JSON Enforcement:** Forces the LLM to return valid structured data, ensuring reliable resume generation.
*   **Formatting Polish:** Automatically handles bullet point cleanup, first-person enforcement, and paragraph spacing.
