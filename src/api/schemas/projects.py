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
    projects: List[ProjectSummary]
    current_projects: List[ProjectSummary]
    previous_projects: List[ProjectSummary]


class ProjectDetail(BaseModel):
    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    root_folder: str = ""
    num_files: int = 0
    size_kb: int = 0
    categories: Dict[str, Any] = Field(default_factory=dict)
    author_count: int = 0
    authors: List[str] = Field(default_factory=list)

    # Tech stack
    languages: List[str] = Field(default_factory=list)
    language_share: Dict[str, float] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list)
    skills_selected: List[str] = Field(default_factory=list)

    # Dependencies
    dependencies_list: List[str] = Field(default_factory=list)
    dependency_files_list: List[str] = Field(default_factory=list)
    build_tools: List[str] = Field(default_factory=list)

    # Authorship
    individual_contributions: Dict[str, Any] = Field(default_factory=dict)
    author_contributions: List[Dict[str, Any]] = Field(default_factory=list)
    contributor_roles: Dict[str, Any] = Field(default_factory=dict)
    collaboration_status: str = "individual"

    # Code metrics
    total_loc: int = 0
    comment_ratio: float = 0.0
    test_file_ratio: float = 0.0
    avg_functions_per_file: float = 0.0
    max_function_length: int = 0

    # Tech profile flags
    has_dockerfile: bool = False
    has_database: bool = False
    has_frontend: bool = False
    has_backend: bool = False
    has_test_files: bool = False
    has_readme: bool = False
    readme_keywords: List[str] = Field(default_factory=list)

    # Skill dimensions
    testing_discipline_level: str = ""
    testing_discipline_score: float = 0.0
    documentation_habits_level: str = ""
    documentation_habits_score: float = 0.0
    modularity_level: str = ""
    modularity_score: float = 0.0
    language_depth_level: str = ""
    language_depth_score: float = 0.0

    # Classifier
    project_type: str = ""

    # Resume insights
    bullets: List[str] = Field(default_factory=list)
    summary: str = ""
    portfolio_entry: str = ""
    thumbnail: Optional[str] = None

    # Scoring
    resume_score: float = 0.0

    # Timestamps
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    import_batch_id: Optional[str] = None


class ProjectDetailResponse(BaseModel):
    ok: bool = True
    project: ProjectDetail
