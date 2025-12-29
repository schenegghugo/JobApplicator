from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "greenhouse"

def parse_greenhouse(html_content: str, company_name: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []

    # Greenhouse Structure 1: Section based
    # usually <section class="level-0"> -> <div class="opening">
    openings = soup.find_all('div', class_='opening')

    for opening in openings:
        link = opening.find('a')
        if not link: continue
        
        href = link.get('href', '')
        if 'gh_jid' not in href and '/jobs/' not in href:
            continue

        full_url = href if href.startswith('http') else f"https://boards.greenhouse.io{href}"
        
        title = link.get_text(strip=True)
        
        loc_span = opening.find('span', class_='location')
        location = loc_span.get_text(strip=True) if loc_span else "Remote/Unknown"

        jobs.append(JobSchema(
            title=title, 
            location=location, 
            url=full_url, 
            company=company_name
        ))

    return jobs
