from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

class JobSchema(BaseModel):
    title: str
    location: str
    url: str
    company: str
    ats_provider: str = "ashby"

def parse_ashby(html_content: str, company_name: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []

    # Ashby usually uses specific classes for job links
    # Often a container with "ashby-job-posting-list"
    # Individual links often contain /posting/ in href
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '')
        
        # Filter for Ashby specific URL patterns
        if '/application/' not in href and '/posting/' not in href:
            continue
            
        # Title is usually inside an h3 or just the text
        text = link.get_text(separator=' ', strip=True)
        
        # Ashby often puts location in a sibling div or child span
        # This is a basic heuristic
        title = text
        location = "Remote/Unknown" # Ashby structure varies wildly by theme

        full_url = href if href.startswith('http') else f"https://jobs.ashbyhq.com{href}"

        jobs.append(JobSchema(
            title=title, 
            location=location, 
            url=full_url, 
            company=company_name
        ))

    return jobs
