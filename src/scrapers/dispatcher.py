from typing import Callable, Optional
from urllib.parse import urlparse

# Import all parsers from your unified module
from src.scrapers.unified_parser import (
    parse_teamtailor,
    parse_greenhouse,
    parse_lever,
    parse_ashby,
    parse_workday,
    parse_smartrecruiters,
    parse_workable,
    parse_talentsoft,      # NEW
    parse_successfactors,  # NEW
    parse_simple,
    JobSchema
)

# Configuration: Domain fragment, Parser function, Readable Name
ATS_RULES = [
    # Global Major ATS
    ("teamtailor.com", parse_teamtailor, "Teamtailor"),
    ("greenhouse.io", parse_greenhouse, "Greenhouse"),
    ("boards.greenhouse.io", parse_greenhouse, "Greenhouse"),
    ("lever.co", parse_lever, "Lever"),
    ("ashbyhq.com", parse_ashby, "Ashby"),
    ("myworkdayjobs.com", parse_workday, "Workday"),
    ("smartrecruiters.com", parse_smartrecruiters, "SmartRecruiters"),
    ("workable.com", parse_workable, "Workable"),
    
    # French / Enterprise Specific
    ("talent-soft.com", parse_talentsoft, "Talentsoft"),
    ("successfactors", parse_successfactors, "SAP SuccessFactors"),
    
    # Custom Portal Overrides
    ("jobs.vinci.com", parse_simple, "Vinci Portal"),
    ("orange.jobs", parse_simple, "Orange Portal"),
]

def detect_ats(url: str) -> Optional[tuple[Callable, str]]:
    """
    Analyzes the URL to determine which ATS system is being used.
    """
    hostname = urlparse(url).netloc.lower()
    full_url = url.lower() # Needed for SuccessFactors which often puts ID in path

    for domain, parser, name in ATS_RULES:
        # Check hostname (most cases) or full URL (for deep paths like SAP)
        if domain in hostname or domain in full_url:
            return parser, name

    return None

def get_parser(url: str) -> tuple[Callable, str]:
    """
    Wrapper around detect_ats. 
    If an ATS is detected, returns that specific parser.
    If NOT detected, returns the generic 'parse_simple' fallback.
    """
    detection = detect_ats(url)
    
    if detection:
        return detection
    
    # Fallback to generic HTML parser
    return parse_simple, "Simple/HTML"
