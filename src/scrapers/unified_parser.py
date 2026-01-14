import re
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List, Optional

# ============================================================
# Shared Schema
# ============================================================

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "simple_html"

# ============================================================
# Shared Helpers
# ============================================================

# Keywords updated for Telecom / Construction / Engineering context
# (Based on Simon's profile)
ROLE_KEYWORDS = [
    # General Engineering & Tech
    "engineer", "ingénieur", "technician", "technicien",
    "developer", "développeur", "data", "network", "réseau",
    "system", "système", "architect", "consultant",

    # Construction & Telecom Specifics
    "conducteur", "travaux", "chantier", "site manager", "works supervisor",
    "chef de projet", "project manager", "pmo", "coordinateur",
    "deployment", "déploiement", "fibre", "ftth", "radio", "mobile",
    "civil", "génie", "construction", "infra",
    
    # Management / General
    "manager", "lead", "head of", "director", "directeur", 
    "responsable", "chargé", "business", "analyst"
]

def matches_role(title: str) -> bool:
    """Case-insensitive check if title contains any keyword."""
    if not title: return False
    title_l = title.lower()
    return any(k in title_l for k in ROLE_KEYWORDS)

def normalize_url(href: str, base: str) -> str:
    """Handles relative URLs, protocol-less URLs, etc."""
    if not href: return ""
    href = href.strip()
    
    if href.startswith("http"): 
        return href
    if href.startswith("//"): 
        return "https:" + href
    if href.startswith("javascript"):
        return ""
    
    # Handle base cleaning for relative paths
    # If base is '.../index.html', strip the file part
    base_clean = base.split("?")[0].rstrip("/")
    if base_clean.endswith(".html") or base_clean.endswith(".aspx") or base_clean.endswith(".php"):
        base_clean = "/".join(base_clean.split("/")[:-1])
        
    return base_clean + "/" + href.lstrip("/")

# ============================================================
# ATS Parsers
# ============================================================

def parse_talentsoft(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    """
    Parser for Talentsoft (Bouygues Telecom, SPIE, GRDF).
    Structure: usually <ul> with class 'offer-list' or divs with 'offer-list-item'.
    """
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    # Look for list items or divs that look like offers
    items = soup.find_all(["li", "div", "tr"], class_=re.compile(r"(offer-list-item|ts-offer-list-item|offer-item|row)", re.I))
    
    for item in items:
        link = item.find("a", href=True)
        if not link: continue
        
        href = link["href"]
        if "candidature" in href or "login" in href: continue
        if href in seen_urls: continue
        
        # Title is often in h3/h4 or spans inside the link
        title_tag = item.find(["h3", "h4", "span"], class_=re.compile(r"title"))
        title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)
        
        if not matches_role(title): continue
        seen_urls.add(href)

        # Location extraction
        loc_tag = item.find(class_=re.compile(r"(place|location|lieu)"))
        location = loc_tag.get_text(strip=True) if loc_tag else "France"

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, url),
            company=company_name, ats_provider="talentsoft"
        ))
    return jobs

def parse_successfactors(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    """
    Parser for SAP SuccessFactors (SNCF, Enedis, RTE).
    Look for links containing 'career_ns=job_listing' or similar SAP patterns.
    """
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"]
        # Standard SF pattern
        if "job_listing" not in href and "career?_run_transaction" not in href:
            continue
            
        if href in seen_urls: continue
        
        title = link.get_text(strip=True)
        if not title: title = link.get("title", "")
        
        if not matches_role(title): continue
        seen_urls.add(href)

        jobs.append(JobSchema(
            title=title, location="France (See URL)",
            url=normalize_url(href, url),
            company=company_name, ats_provider="successfactors"
        ))
    return jobs

def parse_ashby(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/application/" not in href and "/posting/" not in href: continue
        if href in seen_urls: continue
        seen_urls.add(href)
        title = link.get_text(" ", strip=True)
        if not title or not matches_role(title): continue
        jobs.append(JobSchema(title=title, location="Remote/Unknown", url=normalize_url(href, "https://jobs.ashbyhq.com"), company=company_name, ats_provider="ashby"))
    return jobs

def parse_greenhouse(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    for opening in soup.find_all("div", class_="opening"):
        link = opening.find("a", href=True)
        if not link: continue
        href = link["href"]
        if href in seen_urls: continue
        seen_urls.add(href)
        title = link.get_text(strip=True)
        if not matches_role(title): continue
        loc = opening.find("span", class_="location")
        location = loc.get_text(strip=True) if loc else "Remote/Unknown"
        jobs.append(JobSchema(title=title, location=location, url=normalize_url(href, "https://boards.greenhouse.io"), company=company_name, ats_provider="greenhouse"))
    return jobs

def parse_lever(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    for post in soup.find_all("a", class_="posting-title"):
        href = post.get("href")
        if not href or href in seen_urls: continue
        seen_urls.add(href)
        title_tag = post.find("h5", attrs={"data-qa": "posting-name"})
        title = title_tag.get_text(strip=True) if title_tag else post.get_text(strip=True)
        if not matches_role(title): continue
        loc = post.find("span", class_="sort-by-location") or post.find("span", class_="location")
        location = loc.get_text(strip=True) if loc else "Remote/Unknown"
        jobs.append(JobSchema(title=title, location=location, url=normalize_url(href, "https://jobs.lever.co"), company=company_name, ats_provider="lever"))
    return jobs

def parse_teamtailor(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    candidates = soup.find_all(["li", "div", "a"], class_=re.compile(r"(block-grid-item|job-list-item|candidate-job-item)"))
    if not candidates: candidates = soup.find_all("a", href=re.compile(r"/jobs/\d+"))
    for item in candidates:
        link = item if item.name == "a" else item.find("a", href=True)
        if not link: continue
        href = link.get("href", "")
        if "/jobs/" not in href or href in seen_urls: continue
        seen_urls.add(href)
        title_tag = link.find("span", attrs={"title": True})
        title = title_tag.get_text(strip=True) if title_tag else next(iter(link.stripped_strings), "Unknown Role")
        if not matches_role(title): continue
        loc = item.find(class_=re.compile(r"(location|meta-location|text-md)"))
        location = loc.get_text(strip=True) if loc else "France"
        full_url = href if href.startswith("http") else f"https:{href}"
        full_url = full_url.replace("https:https:", "https:") 
        jobs.append(JobSchema(title=title, location=location, url=full_url, company=company_name, ats_provider="teamtailor"))
    return jobs

def parse_workday(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    # Workday requires rendered HTML (handled by Playwright)
    for link in soup.select('a[data-automation-id="jobTitle"]'):
        href = link.get("href")
        if not href or href in seen_urls: continue
        seen_urls.add(href)
        title = link.get_text(strip=True)
        if not matches_role(title): continue
        row = link.find_parent("li")
        loc = row.find("dd", {"data-automation-id": "locations"}) if row else None
        location = loc.get_text(strip=True) if loc else "Unknown"
        jobs.append(JobSchema(title=title, location=location, url=normalize_url(href, url), company=company_name, ats_provider="workday"))
    return jobs

def parse_smartrecruiters(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    for item in soup.select("li.opening-job, a.link--block"):
        link = item if item.name == "a" else item.find("a", href=True)
        if not link: continue
        href = link["href"]
        if href in seen_urls: continue
        seen_urls.add(href)
        title_tag = item.find(["h4", "h3"])
        title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)
        if matches_role(title):
            loc = item.find("span", class_=re.compile("location"))
            location = loc.get_text(strip=True) if loc else "Remote/Unknown"
            jobs.append(JobSchema(title=title, location=location, url=normalize_url(href, "https://careers.smartrecruiters.com"), company=company_name, ats_provider="smartrecruiters"))
    return jobs

def parse_workable(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()
    for item in soup.select('li[data-ui="job-opening"]'):
        link = item.find("a", href=True)
        if not link: continue
        href = link["href"]
        if href in seen_urls: continue
        seen_urls.add(href)
        title_tag = item.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)
        if not matches_role(title): continue
        loc = item.find("span", class_=re.compile("location"))
        location = loc.get_text(strip=True) if loc else "Remote/Unknown"
        jobs.append(JobSchema(title=title, location=location, url=normalize_url(href, "https://apply.workable.com"), company=company_name, ats_provider="workable"))
    return jobs

def parse_simple(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    """
    Robust fallback for Custom Portals (Orange, Vinci, Free).
    Scans for 'Job Cards' (divs) first, then falls back to raw links.
    """
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    # --- Strategy 1: Look for "Job Cards" (div/li/tr with semantic class names) ---
    # This captures Vinci, Orange, etc. much better than raw links
    possible_items = soup.find_all(["div", "li", "tr"], class_=re.compile(r"(job|offer|vacancy|carrieres|result|row|card)", re.I))
    
    for item in possible_items:
        link = item.find("a", href=True)
        if not link: continue
        
        href = link["href"]
        if href in seen_urls or len(href) < 2 or "javascript" in href: continue

        title = link.get_text(strip=True)
        # If link text is generic ("Voir", "Apply"), try to find a Header nearby in the card
        if len(title) < 5 or title.lower() in ["voir l'offre", "postuler", "apply", "view", "details"]:
            heading = item.find(["h2", "h3", "h4", "h5", "span"])
            if heading: title = heading.get_text(strip=True)

        if not matches_role(title): continue

        seen_urls.add(href)
        
        # Try to find location
        loc_text = "France"
        loc_tag = item.find(string=re.compile(r"(Paris|Lyon|Bordeaux|France|Cedex|\d{5})", re.I))
        if loc_tag: loc_text = loc_tag.strip()

        jobs.append(JobSchema(
            title=title, location=loc_text,
            url=normalize_url(href, url),
            company=company_name, ats_provider="simple_heuristic"
        ))

    # --- Strategy 2: Raw Link Scanning (Fallback) ---
    if not jobs:
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Heuristic: Link href usually contains "job", "offer", etc.
            if not re.search(r"(job|career|position|opening|apply|offre|recrutement)", href, re.I): 
                continue
            
            if href in seen_urls: continue
            
            title = link.get_text(strip=True)
            if not title or not matches_role(title): continue
            
            # Skip very short texts (nav items)
            if len(title) < 4: continue

            seen_urls.add(href)
            jobs.append(JobSchema(
                title=title, location="Unknown",
                url=normalize_url(href, url),
                company=company_name, ats_provider="simple_link"
            ))

    return jobs
