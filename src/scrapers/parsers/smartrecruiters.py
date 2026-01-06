def parse_smartrecruiters(html_content: str, company_name: str) -> List[JobSchema]:
    soup = BeautifulSoup(html_content, 'lxml')
    jobs = []
    seen_urls = set()

    for item in soup.select('li.opening-job'):
        link = item.find('a', href=True)
        if not link:
            continue

        href = link['href']
        if href in seen_urls:
            continue
        seen_urls.add(href)

        title_tag = item.find('h4')
        title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)

        loc_tag = item.find('span', class_=re.compile('location'))
        location = loc_tag.get_text(strip=True) if loc_tag else "Unknown"

        full_url = href if href.startswith('http') else f"https://careers.smartrecruiters.com{href}"

        jobs.append(JobSchema(
            title=title,
            location=location,
            url=full_url,
            company=company_name,
            ats_provider="smartrecruiters"
        ))

    return jobs

