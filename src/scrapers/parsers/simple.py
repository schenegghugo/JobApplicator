import re
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "simple_html"

def parse_simple(html_content: str, company_name: str, base_url: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []
    seen_urls = set()

    # Extended Keywords
    ROLE_KEYWORDS = [
        "artist", "compositor", "generalist", "animator", 
        "td", "director", "pipeline", "developer", 
        "producer", "coordinator", "fx", "houdini", "nuke",
        "modeller", "rigger", "lighting", "environment",
        "programmer", "engine", "graphics", "unreal", "unity",
        "supervisor", "lead", "head of", "intern", "trainee"
    ]
    
    # 1. Get all links
    links = soup.find_all('a', href=True)

    for link in links:
        href = link.get('href', '').strip()
        text = link.get_text(" ", strip=True) # Join child tags with space
        
        if not text or len(text) < 3:
            continue
            
        # 2. Filter: Exclude common nav links
        if any(x in text.lower() for x in ['privacy', 'contact', 'home', 'about', 'login', 'read more']):
            continue

        # 3. Validation: Does the text contain a role keyword?
        is_job = any(k in text.lower() for k in ROLE_KEYWORDS)
        
        # 3b. Relaxed Validation for ILP/Fable: 
        # If the URL contains "jobs", "career", or "apply", take it even if text is weird
        if not is_job:
            if any(x in href.lower() for x in ['/job/', '/career/', '/apply']):
                is_job = True

        if not is_job:
            continue

        # 4. URL Construction
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            # Reconstruct domain from base_url
            # e.g. base=https://ilpvfx.com/jobs/ -> domain=https://ilpvfx.com
            parts = base_url.split('/')
            domain = f"{parts[0]}//{parts[2]}"
            full_url = f"{domain}{href}"
        else:
            full_url = f"{base_url.rstrip('/')}/{href}"

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        jobs.append(JobSchema(
            title=text,
            location="Stockholm/Remote", # Default for VFX houses
            url=full_url,
            company=company_name
        ))

    return jobs
