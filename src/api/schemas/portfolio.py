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
    portfolio_customizations: Dict[str, object] = Field(default_factory=dict)


class PortfolioReport(BaseModel):
    id: Optional[int] = None
    title: str = ""
    date_created: Optional[datetime] = None
    sort_by: str = "resume_score"
    notes: Optional[str] = None
    projects: List[PortfolioProject] = Field(default_factory=list)
    portfolio_mode: str = "private"
    portfolio_published_at: Optional[datetime] = None
    public_token: Optional[str] = None
    public_url: Optional[str] = None


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


class PortfolioModeUpdateRequest(BaseModel):
    mode: str  # "private" or "public"


class PortfolioProjectUpdateRequest(BaseModel):
    custom_title: Optional[str] = None
    custom_overview: Optional[str] = None
    custom_achievements: Optional[List[str]] = None
    is_hidden: Optional[bool] = None


class PortfolioPublishResponse(BaseModel):
    ok: bool = True
    portfolio: Optional[PortfolioReport] = None
    message: str = ""

class PortfolioActivityDay(BaseModel):
    date: str
    commits: int = 0
    lines_changed: int = 0
    intensity: int = 0


class PortfolioActivityAggregate(BaseModel):
    total_commits: int = 0
    total_lines_changed: int = 0
    active_days: int = 0


class PortfolioActivityHeatmapRequest(BaseModel):
    report_id: int
    project_names: List[str] = Field(default_factory=list)
    usernames: List[str] = Field(default_factory=list)
    days: Optional[int] = Field(default=None, ge=7, le=3650)

class PortfolioActivityHeatmapResponse(BaseModel):
    ok: bool = True
    report_id: int
    usernames: List[str] = Field(default_factory=list)
    days: int = 84
    generated_at: datetime
    aggregate: PortfolioActivityAggregate
    days_series: List[PortfolioActivityDay] = Field(default_factory=list)

class PortfolioProjectActivity(BaseModel):
    project_name: str
    total_commits: int = 0
    total_lines_changed: int = 0
    active_days: int = 0
    days: List[PortfolioActivityDay] = Field(default_factory=list)
