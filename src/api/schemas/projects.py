"""API data model for project related responses"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProjectSummary(BaseModel):
    id: Optional[int] = None
    name: str

class UploadProjectResponse(BaseModel):
    ok: bool = True
    projects: List[ProjectSummary]

class ProjectsListResponse(BaseModel):
    ok: bool = True
    projects: List[ProjectSummary]

class ProjectDetail(BaseModel):
    id: Optional[int] = None
    name: str
    
    file_path: str = ""
    root_folder: str = ""

    num_files: int = 0
    size_kb: int = 0

    categories: Dict[str, Any] = {}
    authors: List[str] = []

    languages: List[str] = []
    language_share: Dict[str, float] = {}
    frameworks: List[str] = []
    skills_used: List[str] = []

    bullets: List[str] = []
    summary: str = ""
    resume_score: float = 0.0

    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

class ProjectDetailResponse(BaseModel):
    ok: bool = True
    project: ProjectDetail