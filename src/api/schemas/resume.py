from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

SortBy = Literal["resume_score", "date_created", "last_modified"]

class ReportCreateRequest(BaseModel):
    title: Optional[str] = None
    sort_by: SortBy = "resume_score"
    notes: Optional[str] = None
    project_ids: List[int] = Field(default_factory=list)

class ReportSummary(BaseModel):
    id: int
    title: str
    date_created: datetime
    sort_by: SortBy
    notes: Optional[str] = None
    project_count: int

class ReportsListResponse(BaseModel):
    reports: List[ReportSummary]

class ReportDetailResponse(BaseModel):
    # keep light for now; you can add report_projects later if needed
    report: ReportSummary

class ResumeExportRequest(BaseModel):
    report_id: int
    template: str = "jake"
    output_name: str = "resume.pdf"

class ResumeExportResponse(BaseModel):
    ok: bool = True
    export_id: str
    filename: str
    download_url: str