"""API data model for project related responses"""
from pydantic import BaseModel
from typing import List, Optional

class ProjectSummary(BaseModel):
    id: Optional[int] = None
    name: str

class UploadProjectResponse(BaseModel):
    ok: bool = True
    projects: List[ProjectSummary]