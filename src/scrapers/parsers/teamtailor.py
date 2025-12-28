import re
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "teamtailor"

def parse_teamtailor(html_content: str, company_name: str) -> List[JobSchema]:
    """
    Parses generic Teamtailor career pages.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []
    seen_urls = set()

    # Strategy 1: Look for standard job blocks
    candidates = soup.find_all(['li', 'div', 'a'], class_=re.compile(r'(block-grid-item|job-list-item|candidate-job-item)'))

    # Strategy 2: Fallback for List Views
    if not candidates:
        candidates = soup.find_all('a', href=re.compile(r'/jobs/\d+'))

    for item in candidates:
        if item.name == 'a':
            link = item
        else:
            link = item.find('a')
        
        if not link:
            continue

        href = link.get('href', '')
        
        # Strict Filter
        if '/jobs/' not in href or len(href.split('/')) < 3:
            continue
            
        if href in seen_urls:
            continue
        seen_urls.add(href)

        # Title Extraction
        title_tag = link.find('span', attrs={'title': True})
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            text_parts = list(link.stripped_strings)
            title = text_parts[0] if text_parts else "Unknown Role"

        # Location Extraction
        loc_tag = item.find(class_=re.compile(r'(location|meta-location|text-md)'))
        if not loc_tag and item.name == 'a':
            loc_tag = item.find('span', class_='company-location')
            
        location = loc_tag.get_text(strip=True) if loc_tag else "Remote/Stockholm"

        # URL Cleanup
        full_url = href if href.startswith('http') else f"https:{href}"
        if "https:https:" in full_url:
            full_url = full_url.replace("https:https:", "https:")

        jobs.append(JobSchema(
            title=title,
            location=location,
            url=full_url,
            company=company_name
        ))

    return jobs
