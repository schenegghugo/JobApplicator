# JobApplicator

JobApplicator is a local automation suite designed to aggregate, filter, and manage job applications for specific technical roles. It automates the ingestion of job listings from targeted company career portals (ATS), parses unstructured data into a structured SQLite database, and streamlines the application process.

## Project Overview

The system allows for targeted monitoring of high-interest companies, specifically within the Nordic tech and game development sectors. By bypassing generic job boards and querying Applicant Tracking Systems (ATS) directly, it ensures data freshness and access to unadvertised roles.

## Technical Architecture

The application is built in Python and follows a modular ETL (Extract, Transform, Load) architecture:

*   **Extraction Layer:** Uses **Playwright** (headless Chromium) to handle dynamic JavaScript rendering and **BeautifulSoup4** for static HTML parsing. It supports custom parser strategies for different ATS providers (e.g., Teamtailor).
*   **Storage Layer:** A normalized **SQLite** database stores job metadata, full descriptions, and application status, preventing duplicate processing via content hashing.
*   **Processing Layer:** Includes logic for scraping orchestration, robust error handling, and rate limiting to respect server load.
*   **Configuration:** YAML-based configuration for managing target URLs, role keywords, and exclusion criteria without code modification.

## Tech Stack

*   **Language:** Python 3.11+
*   **Web Automation:** Playwright, Requests
*   **Parsing:** BeautifulSoup4, lxml
*   **Data Validation:** Pydantic
*   **Database:** SQLite, SQLAlchemy (Core)
*   **CLI Interface:** Rich

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/schenegghugo/JobApplicator.git
   cd JobApplicator

    Set up the virtual environment:

    bash

python -m venv .venv
source .venv/bin/activate

Install dependencies:

bash

pip install -r requirements.txt
playwright install chromium

Initialize the configuration:
Run the setup script (Linux/Arch) to generate the directory structure and default config files.

bash

    bash setup.sh

Configuration

The system is controlled via config/targets.yaml. Define target URLs under their respective ATS providers:

yaml

teamtailor:
  - https://careers.paradoxplaza.com/jobs
  - https://jobs.fatsharkgames.com/jobs

Usage

1. Scrape Job Listings
Fetches the latest job titles and URLs from configured targets and saves new entries to the database.

bash

python src/run_scraper.py

2. Fetch Job Details
Iterates through new database entries, visits the specific application URLs, and downloads the full HTML descriptions for local analysis.

bash

python src/scrape_details.py

Disclaimer

This tool is intended for personal use to organize job applications. It includes rate-limiting (politeness delays) to minimize server load and adheres to standard web scraping ethics. It is not intended for commercial data resale or aggregation at scale.


