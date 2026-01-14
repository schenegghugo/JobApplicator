from pydantic import BaseModel
from typing import List, Optional

class ExperienceItem(BaseModel):
    role: str
    company: str
    dates: str
    bullets: List[str]

class Basics(BaseModel):
    name: str
    label: str
    email: str
    phone: str
    location: str
    linkedin: Optional[str] = None

class Identity(BaseModel):
    basics: Basics
    bio_base: str
    experience: List[ExperienceItem]
    education: List[dict]
