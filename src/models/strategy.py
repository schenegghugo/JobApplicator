from pydantic import BaseModel
from typing import List, Literal

class Hook(BaseModel):
    name: str
    triggers: List[str]
    inject_into: Literal["bio", "skills", "experience", "cover_letter"]
    content: str

class Strategy(BaseModel):
    settings: dict
    hooks: List[Hook]
