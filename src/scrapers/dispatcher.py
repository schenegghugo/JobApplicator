from typing import Callable, Optional
from urllib.parse import urlparse

# Import all parsers from your single unified module
from src.scrapers.unified_parser import (
    parse_teamtailor,
    parse_greenhouse,
    parse_lever,
    parse_ashby,
    parse_workday,
    parse_smartrecruiters,
    parse_workable
)

ATS_RULES = [
    ("teamtailor.com", parse_teamtailor, "Teamtailor"),
    ("greenhouse.io", parse_greenhouse, "Greenhouse"),
    ("boards.greenhouse.io", parse_greenhouse, "Greenhouse"),
    ("lever.co", parse_lever, "Lever"),
    ("ashbyhq.com", parse_ashby, "Ashby"),
    ("myworkdayjobs.com", parse_workday, "Workday"),
    ("smartrecruiters.com", parse_smartrecruiters, "SmartRecruiters"),
    ("workable.com", parse_workable, "Workable"),
]

def detect_ats(url: str) -> Optional[tuple[Callable, str]]:
    """
    Returns (parser_function, ats_name) or None
    """
    hostname = urlparse(url).netloc.lower()

    for domain, parser, name in ATS_RULES:
        if domain in hostname:
            return parser, name

    return None
