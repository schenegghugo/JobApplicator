
***

# JobApplicator

**JobApplicator** is a local, privacy-focused automation suite designed to streamline the job application process for technical roles. It handles everything from finding the job to generating the final PDF application.

It bypasses generic job boards by scraping company career portals directly, stores data locally, uses **Local AI (LLMs)** to write tailored resumes and cover letters, and compiles them into professional **LaTeX PDFs**.

## Features

*   **🕷️ Automated Scraping:** Ingests job listings directly from ATS providers (e.g., Teamtailor) using Playwright.
*   **💾 Local Data Warehouse:** Stores structured job data in SQLite to prevent duplicate processing.
*   **🧠 AI-Powered Writing:** Uses **Ollama (Llama 3)** to generate tailored cover letters and adjust resumes based on specific job descriptions.
*   **📄 PDF Compilation:** Automatically compiles LaTeX templates into professional PDFs using `pdflatex`.
*   **🖥️ TUI Dashboard:** A central terminal interface to manage the entire pipeline.

## Tech Stack

*   **Core:** Python 3.11+
*   **Web Automation:** Playwright, BeautifulSoup4
*   **Database:** SQLite
*   **AI/LLM:** Ollama (running Llama 3 locally)
*   **Typesetting:** LaTeX (TeX Live)
*   **UI:** Rich (Terminal User Interface)

## Prerequisites

Before running the tool, ensure you have the following installed:

1.  **System Dependencies (Arch Linux Example):**
    You need a working LaTeX distribution to compile the PDFs.
    ```bash
    sudo pacman -S texlive-publishers texlive-fontsextra python-pipx
    ```

2.  **Ollama (Local AI):**
    Install [Ollama](https://ollama.com/) and pull the model:
    ```bash
    ollama pull llama3
    ```

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/schenegghugo/JobApplicator.git
    cd JobApplicator
    ```

2.  **Set up the Virtual Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

4.  **Initialize Directory Structure:**
    ```bash
    bash setup.sh
    ```

## Usage

The easiest way to use JobApplicator is via the main dashboard.

```bash
python main.py
```

### Workflow Steps:

1.  **[1] Run Scraper:** Fetches new job titles/links from configured targets.
2.  **[2] Scrape Details:** Visits each job URL to download the full HTML description.
3.  **[3] Filter/Curate:** (Optional) Review jobs in the database and mark them as `approved` or `rejected`.
4.  **[4] Generate LaTeX:** The AI reads the `approved` jobs and writes a custom `resume.tex` and `cover.tex` for each.
5.  **[5] Compile PDFs:** Compiles the `.tex` files into final `.pdf` documents ready for submission.

## Configuration

### 1. Target Companies
Edit `config/targets.yaml` to add company career pages:

```yaml
teamtailor:
  - https://careers.paradoxplaza.com/jobs
  - https://jobs.fatsharkgames.com/jobs
```

### 2. Candidate Profile
Edit the `CANDIDATE_PROFILE` variable in `src/generate_application.py` to update your personal details, experience, and skills that the AI will use.

### 3. Templates
Customize the base LaTeX templates in:
*   `data/templates/resume.tex`
*   `data/templates/cover.tex`

## Project Structure

```text
JobApplicator/
├── config/             # Configuration files (targets.yaml)
├── data/
│   ├── applications/   # Generated output (One folder per job)
│   ├── db/             # SQLite database (jobs.db)
│   └── templates/      # Base LaTeX templates
├── src/
│   ├── main.py         # Entry point TUI
│   ├── run_scraper.py  # ATS Scraper
│   ├── generate_application.py # AI Content Generation
│   └── compile_pdfs.py # LaTeX Compiler
└── requirements.txt
```

## Disclaimer

This tool is intended for personal use to organize job applications. It includes rate-limiting (politeness delays) to minimize server load. It is not intended for commercial data resale or aggregation at scale. Please respect the `robots.txt` of target websites.
