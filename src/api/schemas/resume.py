from pydantic import BaseModel
from typing import List, Optional

class TodoResponse(BaseModel):
    ok: bool = False
    message: str

class ResumeItemResponse(BaseModel):
    """Resume item representation of a project with textual information."""
    ok: bool = True
    project_id: int
    project_name: str
    summary: str = ""
    bullets: List[str] = []