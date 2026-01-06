import re
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

# ============================================================
# Shared schema
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

ROLE_KEYWORDS = [
    "artist", "compositor", "generalist", "animator",
    "td", "technical", "pipeline", "developer",
    "programmer", "engineer", "graphics",
    "fx", "houdini", "nuke", "lighting",
    "modeller", "modeler", "rigger",
    "environment", "unreal", "unity",
    "producer", "coordinator", "supervisor",
    "lead", "head of", "intern", "trainee"
]

def matches_role(title: str) -> bool:
    title_l = title.lower()
    return any(k in title_l for k in ROLE_KEYWORDS)

def normalize_url(href: str, base: str) -> str:
    if href.startswith("http"): return href
    if href.startswith("//"): return "https:" + href
    return base.rstrip("/") + "/" + href.lstrip("/")

# ============================================================
# Parsers (Standardized Signature: html, company, current_page_url)
# ============================================================

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

        jobs.append(JobSchema(
            title=title, location="Remote/Unknown",
            url=normalize_url(href, "https://jobs.ashbyhq.com"),
            company=company_name, ats_provider="ashby"
        ))
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

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, "https://boards.greenhouse.io"),
            company=company_name, ats_provider="greenhouse"
        ))
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

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, "https://jobs.lever.co"),
            company=company_name, ats_provider="lever"
        ))
    return jobs

def parse_teamtailor(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    candidates = soup.find_all(["li", "div", "a"], class_=re.compile(r"(block-grid-item|job-list-item|candidate-job-item)"))
    if not candidates:
        candidates = soup.find_all("a", href=re.compile(r"/jobs/\d+"))

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
        location = loc.get_text(strip=True) if loc else "Remote/Stockholm"
        
        full_url = href if href.startswith("http") else f"https:{href}"
        full_url = full_url.replace("https:https:", "https:") # Safety fix

        jobs.append(JobSchema(
            title=title, location=location,
            url=full_url, company=company_name, ats_provider="teamtailor"
        ))
    return jobs

def parse_workday(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    for link in soup.select('a[data-automation-id="jobTitle"]'):
        href = link.get("href")
        if not href or href in seen_urls: continue
        seen_urls.add(href)

        title = link.get_text(strip=True)
        if not matches_role(title): continue

        row = link.find_parent("li")
        loc = row.find("dd", {"data-automation-id": "locations"}) if row else None
        location = loc.get_text(strip=True) if loc else "Remote/Unknown"

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, url), # Uses current page URL as base
            company=company_name, ats_provider="workday"
        ))
    return jobs

def parse_smartrecruiters(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    for item in soup.select("li.opening-job"):
        link = item.find("a", href=True)
        if not link: continue
        href = link["href"]
        if href in seen_urls: continue
        seen_urls.add(href)

        title_tag = item.find("h4")
        title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)
        if not matches_role(title): continue

        loc = item.find("span", class_=re.compile("location"))
        location = loc.get_text(strip=True) if loc else "Remote/Unknown"

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, "https://careers.smartrecruiters.com"),
            company=company_name, ats_provider="smartrecruiters"
        ))
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

        jobs.append(JobSchema(
            title=title, location=location,
            url=normalize_url(href, "https://apply.workable.com"),
            company=company_name, ats_provider="workable"
        ))
    return jobs

def parse_simple(html_content: str, company_name: str, url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, "lxml")
    jobs, seen_urls = [], set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not re.search(r"(job|career|position|opening)", href, re.I): continue
        if href in seen_urls: continue
        
        title = link.get_text(strip=True)
        if not title or not matches_role(title): continue

        seen_urls.add(href)
        jobs.append(JobSchema(
            title=title, location="Remote/Unknown",
            url=normalize_url(href, url),
            company=company_name, ats_provider="simple_html"
        ))
    return jobs
