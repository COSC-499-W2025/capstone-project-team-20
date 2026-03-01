from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from collections import Counter
import tempfile, shutil
from uuid import uuid4
from pydantic import BaseModel

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ConsentManager import ConsentManager
from src.managers.ProjectManager import ProjectManager
from src.managers.ReportManager import ReportManager
from src.exporters.ReportExporter import ReportExporter
from src.generators.PortfolioGenerator import PortfolioGenerator
from src.ZipParser import parse_zip_to_project_folders
from src.services.badge_wrapped_service import build_badge_progress, build_yearly_wrapped
from src.api.schemas.skills import SkillsListResponse, SkillItem
from src.api.schemas.projects import (
    UploadProjectResponse,
    ProjectsListResponse,
    ProjectSummary,
    ProjectDetailResponse,
    ProjectDetail,
)
from src.api.schemas.consent import ConsentResponse, ConsentRequest
from src.api.schemas.badges import BadgeProgressResponse, YearlyWrappedResponse
from src.api.schemas.resume import (
    ResumeExportRequest, ResumeExportResponse,
    ReportsListResponse, ReportSummary, ReportDetailResponse, ReportCreateRequest
)
from src.api.schemas.portfolio import (
    PortfolioDetailsGenerateRequest, PortfolioDetailsGenerateResponse,
    PortfolioExportRequest, PortfolioExportResponse
)

from src.api.schemas import (
  SkillsListResponse, SkillItem, PortfolioResponse, ConsentResponse, UploadProjectResponse, ProjectsListResponse, ProjectSummary,
  ProjectDetailResponse, ProjectDetail, PortfolioGenerateRequest, PortfolioGenerateResponse, PortfolioUpdateRequest,
  PortfolioReport, PortfolioProject, PortfolioDetailsResponse
)

"""For all our routes. Requirement 32, endpoints"""
router = APIRouter()

def _build_portfolio_project(project) -> PortfolioProject:
    details = project.portfolio_details
    details_payload = details.to_dict() if hasattr(details, "to_dict") else {}
    return PortfolioProject(
        project_name=project.project_name,
        resume_score=project.resume_score,
        portfolio_details=PortfolioDetailsResponse(**details_payload),
        languages=list(project.languages or []),
        language_share=dict(project.language_share or {}),
        frameworks=list(project.frameworks or []),
        date_created=project.date_created,
        last_modified=project.last_modified,
        collaboration_status=project.collaboration_status,
    )

def _build_portfolio_report(report) -> PortfolioReport:
    projects = [_build_portfolio_project(p) for p in (report.projects or [])]
    return PortfolioReport(
        id=report.id,
        title=report.title,
        date_created=report.date_created,
        sort_by=report.sort_by,
        notes=report.notes,
        projects=projects,
    )
def _copy_upload_to_temp_zip(upload: UploadFile) -> Path:
    """Persist an uploaded ZIP to a temp file, resetting stream position first."""
    if getattr(upload, "file", None) and hasattr(upload.file, "seek"):
        upload.file.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(upload.file, tmp)

    return tmp_path

def require_consent():
    cm = ConsentManager()
    if not cm.has_user_consented():
        raise HTTPException(
            status_code=403,
            detail="User consent required before generating reports or exports."
        )
    return True

class UploadPathRequest(BaseModel):
    path: str

def _run_post_upload_analyses(analyzer: ProjectAnalyzer, projects):
    """Run non-interactive analyses so uploaded projects have usable dashboard data."""
    for method_name in ("analyze_git_and_contributions", "analyze_metadata", "analyze_categories", "analyze_languages", "analyze_skills"):
        method = getattr(analyzer, method_name, None)
        if callable(method):
            if method_name == "analyze_skills":
                method(projects=projects, silent=True)
            elif method_name == "analyze_git_and_contributions":
                method(projects=projects, interactive=False)
            else:
                method(projects=projects)

@router.post("/projects/upload-path", dependencies=[Depends(require_consent)])
def upload_project_from_path(req: UploadPathRequest):
    """
    Dev-only endpoint: load a ZIP file from a local path on the backend.
    WARNING: This endpoint is for development/testing only.
    DO NOT expose in production as it allows arbitrary path access on the API host.
    """
    zip_path = Path(req.path)

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="File not found at given path.")

    root_folders = parse_zip_to_project_folders(str(zip_path))
    if not root_folders:
        raise HTTPException(status_code=400, detail="Zip parsed no projects.")

    analyzer = ProjectAnalyzer(ConfigManager(), root_folders, zip_path)
    created_projects = analyzer.initialize_projects()
    _run_post_upload_analyses(analyzer, created_projects)

    return {
        "projects": [
            {"id": p.id, "name": p.name}
            for p in created_projects
        ]
    }

@router.post("/projects/upload", response_model=UploadProjectResponse, status_code=status.HTTP_201_CREATED)
def upload_project(zip_file: UploadFile = File(...)):
    """Upload a zip file, analyze projects inside, and persist project records."""
    tmp_path = _copy_upload_to_temp_zip(zip_file)

    root_folders = parse_zip_to_project_folders(str(tmp_path))
    if not root_folders:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Zip parsed no projects (invalid or empty zip.)")
    analyzer = ProjectAnalyzer(ConfigManager(), root_folders, tmp_path)
    created_projects = analyzer.initialize_projects()
    _run_post_upload_analyses(analyzer, created_projects)

    tmp_path.unlink(missing_ok=True)

    return UploadProjectResponse(
        projects=[ProjectSummary(id=p.id, name=p.name) for p in created_projects]
    )

@router.post("/privacy-consent", response_model=ConsentResponse)
def upload_consent(req: ConsentRequest):
    """Set the user's privacy consent flag (required for reporting/export features)."""
    cm = ConsentManager()
    cm.set_consent(req.consent)
    return ConsentResponse(consent=req.consent)

@router.get("/projects", response_model=ProjectsListResponse)
def get_list_projects():
    """List all analyzed/uploaded projects."""
    pm = ProjectManager()
    projects = pm.get_all()
    return ProjectsListResponse(
        projects=[ProjectSummary(id=p.id, name=p.name) for p in projects]
    )

@router.get("/projects/{id}", response_model=ProjectDetailResponse)
def get_project(id: int):
    """Get metadata/details for a project by id."""
    pm = ProjectManager()
    project = pm.get(id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ProjectDetailResponse(
        project=ProjectDetail(**project.__dict__)
    )

@router.delete("/projects/{id}", status_code=204)
def delete_project(id: int):
    """
    Delete a project by id. (Removes record and associated data.)
    Returns 204 No Content on success.
    """
    pm = ProjectManager()
    project = pm.get(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    deleted = pm.delete(id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete project.")

    return None

@router.get("/skills", response_model=SkillsListResponse)
def get_skills_list():
    """List unique skills detected across all projects, plus their project usage count."""
    pm = ProjectManager()
    projects = list(pm.get_all())

    counts = Counter()

    for p in projects:
        for s in (p.skills_used or []):
            if s:
                counts[s.strip()] += 1

    skills = [
        SkillItem(name=name, project_count=count)
        for name, count in sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))
    ]

    return SkillsListResponse(skills=skills)

@router.get("/badges/progress", response_model=BadgeProgressResponse)
def get_badge_progress():
    """Return badge progress analytics based on current projects."""
    pm = ProjectManager()
    return build_badge_progress(list(pm.get_all()))


@router.get("/wrapped/yearly", response_model=YearlyWrappedResponse)
def get_yearly_wrapped():
    """Return 'yearly wrapped' analytics for projects."""
    pm = ProjectManager()
    return build_yearly_wrapped(list(pm.get_all()))

# ---------------------------
# Reports (saved templates)
# ---------------------------

@router.post("/reports", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_consent)])
def create_report(req: ReportCreateRequest):
    """
    Create a saved Report (template) from a list of Project IDs.
    Snapshots projects into ReportProjects in reports.db.
    """
    from src.models.Report import Report
    from src.models.ReportProject import ReportProject, PortfolioDetails

    pm = ProjectManager()
    rm = ReportManager()

    report = Report(
        title=req.title or "",
        sort_by=req.sort_by,
        notes=req.notes,
        projects=[]
    )

    for pid in req.project_ids:
        p = pm.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail=f"Project {pid} not found.")

        pd = getattr(p, "portfolio_details", None)
        if isinstance(pd, dict):
            pd = PortfolioDetails.from_dict(pd)
        elif pd is None:
            pd = PortfolioDetails()
        rp = ReportProject(
            project_name=p.name,
            resume_score=getattr(p, "resume_score", 0.0) or 0.0,
            bullets=p.bullets or [],
            summary=getattr(p, "summary", "") or "",
            portfolio_details=pd,
            languages=p.languages or [],
            language_share=p.language_share or {},
            frameworks=p.frameworks or [],
            date_created=p.date_created,
            last_modified=p.last_modified,
            collaboration_status=getattr(p, "collaboration_status", "individual") or "individual",
        )

        report.add_project(rp)

    report_id = rm.create_report(report)
    saved = rm.get_report(report_id)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to create report.")

    return ReportDetailResponse(
        report=ReportSummary(
            id=saved.id,
            title=saved.title,
            date_created=saved.date_created,
            sort_by=saved.sort_by,
            notes=saved.notes,
            project_count=saved.project_count,
        )
    )


@router.get("/reports", response_model=ReportsListResponse, dependencies=[Depends(require_consent)])
def list_reports():
    """List all saved reports (templates) in the system."""
    rm = ReportManager()
    reports = rm.list_reports()
    return ReportsListResponse(
        reports=[
            ReportSummary(
                id=r.id,
                title=r.title,
                date_created=r.date_created,
                sort_by=r.sort_by,
                notes=r.notes,
                project_count=r.project_count,
            )
            for r in reports
        ]
    )

@router.get("/reports/{id}", response_model=ReportDetailResponse, dependencies=[Depends(require_consent)])
def get_report(id: int):
    """Get a report (by id) and its summary info."""
    rm = ReportManager()
    r = rm.get_report(id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ReportDetailResponse(
        report=ReportSummary(
            id=r.id,
            title=r.title,
            date_created=r.date_created,
            sort_by=r.sort_by,
            notes=r.notes,
            project_count=r.project_count,
        )
    )

@router.delete("/reports/{id}", status_code=204, dependencies=[Depends(require_consent)])
def delete_report(id: int):
    """
    Delete a report and all associated report projects.
    Returns 204 No Content on success.
    """
    rm = ReportManager()
    report = rm.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    deleted = rm.delete_report(id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete report.")

    return None

@router.get("/portfolio/{id}", response_model=PortfolioResponse)
def get_portfolio(id: int):
    """Retrieve a generated portfolio report by id."""
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    portfolio = _build_portfolio_report(report)
    return PortfolioResponse(ok=True, portfolio=portfolio, message="Portfolio retrieved.")

@router.post("/portfolio/export", response_model=PortfolioExportResponse)
def export_portfolio(req: PortfolioExportRequest):
    """
    Export a portfolio PDF file from a report and return download info.
    """
    rm = ReportManager()
    report = rm.get_report(req.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    try:
        export_id, out_path = export_report_pdf(report, template="portfolio", output_name=req.output_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PortfolioExportResponse(
        export_id=export_id,
        filename=out_path.name,
        download_url=f"/portfolio/exports/{export_id}/download"
    )

@router.get("/portfolio/exports/{export_id}/download", dependencies=[Depends(require_consent)])
def download_portfolio(export_id: str):
    """Download a previously exported portfolio file."""
    out_dir = Path("portfolios")
    matches = list(out_dir.glob(f"{export_id}-*.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="Export not found.")
    p = matches[0]
    return FileResponse(str(p), filename=p.name)

@router.post("/portfolio/{id}/edit", response_model=PortfolioResponse)
def edit_portfolio(id: int, payload: PortfolioUpdateRequest):
    """
    Edit an existing portfolio report's title and notes.
    """
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    if payload.title:
        report.title = payload.title.strip()
    if payload.notes is not None:
        report.notes = payload.notes
    report_manager.update_report(report)
    portfolio = _build_portfolio_report(report)
    return PortfolioResponse(ok=True, portfolio=portfolio, message="Portfolio updated.")

@router.post(
    "/reports/{id}/portfolio-details/generate",
    response_model=PortfolioDetailsGenerateResponse,
    dependencies=[Depends(require_consent)]
)
def generate_report_portfolio_details(id: int, req: PortfolioDetailsGenerateRequest):
    """
    Generates PortfolioDetails for selected ReportProjects in a report
    using the analyzed Project stored in projects.db (matched by name),
    then persists changes back into reports.db.
    """
    if req.report_id != id:
        raise HTTPException(status_code=400, detail="report_id mismatch.")

    rm = ReportManager()
    report = rm.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    pm = ProjectManager()
    updated = []
    targets = set(req.project_names)

    for rp in report.projects:
        if rp.project_name not in targets:
            continue

        p = pm.get_by_name(rp.project_name)
        if not p:
            raise HTTPException(status_code=404, detail=f"Project '{rp.project_name}' not found in projects DB.")

        metadata = {
            "start_date": (p.date_created.isoformat()[:10] if p.date_created else None),
            "end_date": (p.last_modified.isoformat()[:10] if p.last_modified else None),
        }

        categorized_files = p.categories or {}
        language_share = p.language_share or {}
        language_list = p.languages or list(language_share.keys())

        details = PortfolioGenerator(
            metadata=metadata,
            categorized_files=categorized_files,
            language_share=language_share,
            project=p,
            language_list=language_list,
        ).generate_portfolio_details()

        rp.portfolio_details = details
        updated.append(rp.project_name)

    rm.update_report(report)
    return PortfolioDetailsGenerateResponse(updated_project_names=updated)

def export_report_pdf(report, template: str, output_name: str) -> tuple[str, Path]:
    export_id = uuid4().hex
    out_dir = Path("resumes") if template != "portfolio" else Path("portfolios")
    out_dir.mkdir(exist_ok=True)

    safe_name = output_name.replace("/", "_")
    out_path = out_dir / f"{export_id}-{safe_name}"

    ReportExporter().export_to_pdf(
        report=report,
        config_manager=ConfigManager(),
        output_path=str(out_path),
        template=template
    )

    if not out_path.exists():
        raise HTTPException(status_code=500, detail="Export failed: output file not created.")
    return export_id, out_path

@router.post("/resume/export", response_model=ResumeExportResponse, dependencies=[Depends(require_consent)])
def export_resume(req: ResumeExportRequest):
    """
    Export a resume PDF file from a report and return download info.
    """
    rm = ReportManager()
    report = rm.get_report(req.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    try:
        export_id, out_path = export_report_pdf(report, template=req.template, output_name=req.output_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ResumeExportResponse(
        export_id=export_id,
        filename=out_path.name,
        download_url=f"/resume/exports/{export_id}/download"
    )

@router.get("/resume/exports/{export_id}/download", dependencies=[Depends(require_consent)])
def download_resume(export_id: str):
    """Download a previously exported resume file."""
    out_dir = Path("resumes")
    matches = list(out_dir.glob(f"{export_id}-*.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="Export not found.")
    p = matches[0]
    return FileResponse(str(p), filename=p.name)
