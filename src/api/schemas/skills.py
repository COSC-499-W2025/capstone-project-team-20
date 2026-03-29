from pydantic import BaseModel
from typing import List

class SkillItem(BaseModel):
    name: str
    project_count: int

class SkillUsageItem(SkillItem):
    projects: List[str]

class SkillsListResponse(BaseModel):
    ok: bool = True
    skills: List[SkillItem]


class SkillsUsageResponse(BaseModel):
    ok: bool = True
    skills: List[SkillUsageItem]
