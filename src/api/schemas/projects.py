"""API data model for project related responses"""
from pydantic import BaseModel, Field
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

    categories: Dict[str, Any] = Field(default_factory=dict)
    authors: List[str] = Field(default_factory=list)
    contributor_roles: Dict[str, Any] = Field(default_factory=dict)

    languages: List[str] = Field(default_factory=list)
    language_share: Dict[str, float] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list)

    bullets: List[str] = Field(default_factory=list)
    summary: str = ""
    resume_score: float = 0.0

    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

class ProjectDetailResponse(BaseModel):
    ok: bool = True
    project: ProjectDetail
