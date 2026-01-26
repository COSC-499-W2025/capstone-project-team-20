from pydantic import BaseModel
from typing import List

class SkillItem(BaseModel):
    name: str
    project_count: int

class SkillsListResponse(BaseModel):
    ok: bool = True
    skills: List[SkillItem]