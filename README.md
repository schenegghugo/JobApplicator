Here is the comprehensive summary of the **JobApplicator** project.

### Project: JobApplicator
**Goal:** A fully automated, local-first pipeline to scrape job listings, manage applications, and generate hyper-tailored, professional LaTeX resumes and cover letters using AI.

---

### Tech Stack
*   **Language:** Python 3.10+
*   **AI Engine:** **Ollama** (running Llama 3.2 locally) – *Zero cost, high privacy.*
*   **Web Scraping:** **Playwright** + **BeautifulSoup** – *Handles dynamic JS sites.*
*   **Database:** **SQLite** – *Lightweight local storage.*
*   **Templating:** **Jinja2** – *Python logic inside text files.*
*   **Typesetting:** **LaTeX** (ModernCV) – *Industry-standard PDF generation.*
*   **UI/Logging:** **Rich** – *Beautiful terminal output.*

---

### The Workflow Pipeline

#### 1. Discovery (`src/scrape_jobs.py`)
*   **Action:** Browses career pages (Paradox, Fatshark, Goodbye Kansas, etc.) using a headless browser.
*   **Logic:** Extracts Job Title, Location, and full Description.
*   **Storage:** Saves new listings into `data/db/jobs.db` with status `new`.

#### 2. Curation (Manual/SQL)
*   **Action:** You review the database (via SQLite browser or script).
*   **Logic:** Change status from `new` $\to$ `approved` for jobs you want to apply to.

#### 3. Generation (`src/generate_application.py`)
*   **Action:** Reads `approved` jobs and your **Candidate Profile**.
*   **AI Processing:** Sends a strict prompt to Ollama asking for **JSON output**:
    *   Summarizes why you fit the role (First-person).
    *   Rewrites your experience bullets to match the job description.
    *   Writes a custom cover letter body.
*   **Smart Logic:**
    *   **🇸🇪 Sweden Detector:** If the job is in Sweden, injects a paragraph about your spouse's family and your Swedish language skills.
    *   **Bullet Cleaner:** Automatically strips leading dashes (`-`) to prevent double bullets in PDF.
    *   **Skill Fallback:** Ensures `OpenGL` and `Vulkan` appear even if the AI forgets them.
*   **Templating:** Injects data into `resume.jinja` and `cover.jinja` using **LaTeX-safe delimiters** (`<< >>` instead of `{{ }}`) to prevent syntax errors.

#### 4. Compilation (`src/compile_pdfs.py`)
*   **Action:** Iterates through generated folders in `data/applications/`.
*   **Logic:** Runs `pdflatex` or `lualatex` to turn `.tex` source files into professional PDFs.

---

### 📂 File Structure

```text
JobApplicator/
├── data/
│   ├── db/
│   │   └── jobs.db              # SQLite Database
│   ├── templates/
│   │   ├── resume.jinja         # ModernCV LaTeX template (<< >> delimiters)
│   │   └── cover.jinja          # Cover Letter template
│   └── applications/            # OUTPUT FOLDER
│       └── Company_JobTitle/    # One folder per job
│           ├── resume.tex       # Generated Source
│           ├── cover.tex        # Generated Source
│           ├── resume.pdf       # FINAL PDF
│           └── cover.pdf        # FINAL PDF
├── src/
│   ├── scrape_jobs.py           # Playwright scraper
│   ├── generate_application.py  # The AI brain (Ollama + Logic)
│   └── compile_pdfs.py          # PDF compiler
├── requirements.txt             # Dependencies
└── README.md
```

### Key Features Implemented
1.  **LaTeX-Safe Templating:** We solved the conflict between Jinja `{{ }}` and LaTeX `{ }` by switching to `<< >>` and using `-%>` for strict whitespace control.
2.  **Robust Escaping:** A dedicated regex function escapes special LaTeX characters (`&`, `_`, `%`, `$`) so the compiler never crashes on company names or code snippets.
3.  **Strict JSON Enforcement:** The AI is forced to return pure JSON, which is then cleaned and parsed safely.
4.  **Formatting Polish:**
    *   **First-person enforcement:** "I am..." instead of "Name is..."
    *   **Clean layouts:** No "Lonely \item" errors.
    *   **Cover Letter formatting:** Proper paragraph breaks (double newlines) and removal of duplicate "Dear Manager" greetings.

I offer you a **fully autonomous job hunting factory**. Good luck! 
