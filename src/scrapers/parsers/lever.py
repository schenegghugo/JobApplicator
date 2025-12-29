from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "lever"

def parse_lever(html_content: str, company_name: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []

    # Lever usually lists jobs as <a class="posting-title">
    postings = soup.find_all('a', class_='posting-title')

    for post in postings:
        href = post.get('href', '')
        
        title_tag = post.find('h5', attrs={'data-qa': 'posting-name'})
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Role"
        
        # Location is usually in a span class="sort-by-location" or "location"
        loc_tag = post.find('span', class_='sort-by-location')
        if not loc_tag:
            loc_tag = post.find('span', class_='location')
            
        location = loc_tag.get_text(strip=True) if loc_tag else "Remote/Unknown"

        jobs.append(JobSchema(
            title=title, 
            location=location, 
            url=href, 
            company=company_name
        ))

    return jobs
