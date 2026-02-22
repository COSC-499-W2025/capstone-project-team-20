from pydantic import BaseModel, Field
from typing import List

class PortfolioDetailsGenerateRequest(BaseModel):
    report_id: int
    project_names: List[str] = Field(..., min_length=1)  # report snapshot uses names

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