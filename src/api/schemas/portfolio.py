from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class PortfolioContributorRole(BaseModel):
    name: str
    role: str
    confidence: float = 0.0
    confidence_pct: int = 0


class PortfolioDetailsResponse(BaseModel):
    project_name: str = ""
    role: str = ""
    timeline: str = ""
    technologies: str = ""
    overview: str = ""
    achievements: List[str] = Field(default_factory=list)
    contributor_roles: List[PortfolioContributorRole] = Field(default_factory=list)


class PortfolioProject(BaseModel):
    project_name: str
    resume_score: float = 0.0
    summary: str = ""
    bullets: List[str] = Field(default_factory=list)
    portfolio_details: PortfolioDetailsResponse
    languages: List[str] = Field(default_factory=list)
    language_share: Dict[str, float] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    collaboration_status: str = "individual"


class PortfolioReport(BaseModel):
    id: Optional[int] = None
    title: str = ""
    date_created: Optional[datetime] = None
    sort_by: str = "resume_score"
    notes: Optional[str] = None
    projects: List[PortfolioProject] = Field(default_factory=list)


class PortfolioGenerateRequest(BaseModel):
    report_id: int
    output_filename: Optional[str] = None


class PortfolioGenerateResponse(BaseModel):
    ok: bool = True
    report_id: int
    output_path: str
    message: str = "Portfolio generated."


class PortfolioUpdateRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None


class PortfolioResponse(BaseModel):
    ok: bool = True
    portfolio: Optional[PortfolioReport] = None
    message: str = ""


class PortfolioDetailsGenerateRequest(BaseModel):
    report_id: int
    project_names: List[str] = Field(..., min_length=1)


class PortfolioDetailsGenerateResponse(BaseModel):
    ok: bool = True
    updated_project_names: List[str]


class PortfolioExportRequest(BaseModel):
    report_id: int
    output_name: str = "portfolio.pdf"


class PortfolioExportResponse(BaseModel):
    ok: bool = True
    export_id: str
    filename: str
    download_url: str
