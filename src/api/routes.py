from typing import Any, List, Optional

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
    PortfolioExportRequest, PortfolioExportResponse,
    PortfolioModeUpdateRequest, PortfolioProjectUpdateRequest, PortfolioPublishResponse
)
from src.api.schemas import (
    PortfolioResponse, PortfolioUpdateRequest, PortfolioReport, PortfolioProject, PortfolioDetailsResponse
)

"""For all our routes. Requirement 32, endpoints"""
router = APIRouter()


def _build_portfolio_project(project) -> PortfolioProject:
    details = project.portfolio_details
    details_payload = details.to_dict() if hasattr(details, "to_dict") else {}
    custom = dict(getattr(project, "portfolio_customizations", {}) or {})

    custom_title = (custom.get("custom_title") or "").strip()
    custom_overview = (custom.get("custom_overview") or "").strip()
    custom_achievements = custom.get("custom_achievements")
    if not isinstance(custom_achievements, list):
        custom_achievements = None

    if custom_title:
        details_payload["project_name"] = custom_title
    if custom_overview:
        details_payload["overview"] = custom_overview
    if custom_achievements is not None:
        details_payload["achievements"] = [str(x).strip() for x in custom_achievements if str(x).strip()]

    return PortfolioProject(
        project_name=project.project_name,
        resume_score=project.resume_score,
        summary=getattr(project, "summary", "") or "",
        bullets=list(getattr(project, "bullets", []) or []),
        portfolio_details=PortfolioDetailsResponse(**details_payload),
        portfolio_customizations=custom,
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
        portfolio_mode=getattr(report, "portfolio_mode", "private") or "private",
        portfolio_published_at=getattr(report, "portfolio_published_at", None),
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

class ContributorMergeResolutionRequest(BaseModel):
    canonical: str
    merge: List[str]


class ContributorMergeApplyRequest(BaseModel):
    project_id: int
    resolutions: List[ContributorMergeResolutionRequest]


class ContributorMergeBatchRequest(BaseModel):
    projects: List[ContributorMergeApplyRequest]


class ReportProjectPatchRequest(BaseModel):
    project_name: Optional[str] = None
    stack_languages: Optional[List[str]] = None
    stack_frameworks: Optional[List[str]] = None
    bullets: Optional[List[str]] = None

class ConfigSetRequest(BaseModel):
    key: str
    value: Any


def _run_post_upload_analyses(analyzer: ProjectAnalyzer, projects):
    changed = [p for p in projects if p.name in analyzer.changed_project_names]
    pending_duplicates = []

    if not changed:
        return pending_duplicates

    pending_duplicates = analyzer.analyze_git_and_contributions(projects=changed, interactive=False) or []

    pending_ids = {p["project_id"] for p in pending_duplicates}
    clean = [p for p in changed if p.id not in pending_ids]

    for method_name in ("analyze_metadata", "analyze_categories", "analyze_languages", "analyze_skills", "generate_insights_noninteractive"):
        method = getattr(analyzer, method_name, None)
        if not callable(method):
            continue
        if method_name == "analyze_skills":
            method(projects=clean, silent=True)
        else:
            method(projects=clean)

    return pending_duplicates


def _require_report_kind(report, expected_kind: str):
    actual_kind = getattr(report, "report_kind", "resume") or "resume"
    if actual_kind != expected_kind:
        raise HTTPException(
            status_code=400,
            detail=f"This endpoint only supports '{expected_kind}' reports."
        )


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
    pending_duplicates = _run_post_upload_analyses(analyzer, created_projects)

    return {
        "ok": True,
        "status": "needs_resolution" if pending_duplicates else "complete",
        "projects": [{"id": p.id, "name": p.name} for p in created_projects],
        "pending_duplicates": pending_duplicates,
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
    pending_duplicates = _run_post_upload_analyses(analyzer, created_projects)
    tmp_path.unlink(missing_ok=True)
    return UploadProjectResponse(
        ok=True,
        status="needs_resolution" if pending_duplicates else "complete",
        projects=[ProjectSummary(id=p.id, name=p.name) for p in created_projects],
        pending_duplicates=pending_duplicates,
        )


@router.get("/privacy-consent", response_model=ConsentResponse)
def get_consent():
    """Return the user's current privacy consent status."""
    cm = ConsentManager()
    return ConsentResponse(consent=cm.has_user_consented())


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
    grouped_projects = pm.get_project_groups()
    current_projects = [ProjectSummary(id=p.id, name=p.name) for p in grouped_projects["current"]]
    previous_projects = [ProjectSummary(id=p.id, name=p.name) for p in grouped_projects["previous"]]
    return ProjectsListResponse(
        projects=current_projects + previous_projects,
        current_projects=current_projects,
        previous_projects=previous_projects,
    )


@router.post("/projects/clear", response_model=dict)
def clear_projects():
    """Development helper: remove all projects from storage."""
    pm = ProjectManager()
    pm.clear()
    return {"ok": True}


@router.get("/projects/{id}", response_model=ProjectDetailResponse)
def get_project(id: int):
    """Get metadata/details for a project by id."""
    pm = ProjectManager()
    project = pm.get(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectDetailResponse(project=ProjectDetail(**project.__dict__))


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
    return None

@router.post("/projects/resolve-contributors")
def resolve_contributors(req: ContributorMergeApplyRequest):
    pm = ProjectManager()
    project = pm.get(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    analyzer = ProjectAnalyzer(
        ConfigManager(),
        root_folders=[],
        zip_path=Path(project.file_path)
    )

    result = analyzer.apply_contributor_merge_resolutions(
        project_id=req.project_id,
        resolutions=[r.model_dump() for r in req.resolutions],
    )

    return {"ok": True, **result}


@router.post("/projects/resolve-contributors-batch")
def resolve_contributors_batch(req: ContributorMergeBatchRequest):
    """Resolve contributor duplicates for multiple projects in a single request."""
    pm = ProjectManager()
    results = []

    for item in req.projects:
        project = pm.get(item.project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {item.project_id} not found.")

        analyzer = ProjectAnalyzer(
            ConfigManager(),
            root_folders=[],
            zip_path=Path(project.file_path)
        )

        result = analyzer.apply_contributor_merge_resolutions(
            project_id=item.project_id,
            resolutions=[r.model_dump() for r in item.resolutions],
        )
        results.append({"project_id": item.project_id, **result})

    return {"ok": True, "results": results}


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
    report = Report(title=req.title or "", sort_by=req.sort_by, notes=req.notes, report_kind=req.report_kind, projects=[])

    for pid in req.project_ids:
        p = pm.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail=f"Project {pid} not found.")

        pd = getattr(p, "portfolio_details", None)
        if isinstance(pd, dict):
            pd = PortfolioDetails.from_dict(pd)
        elif pd is None:
            pd = PortfolioDetails()

        if not p.bullets or not p.summary:
            analyzer = ProjectAnalyzer(ConfigManager(), root_folders=[], zip_path=Path(p.file_path))
            analyzer.generate_insights_noninteractive(projects=[p])
            p = pm.get(pid)

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
            report_kind=saved.report_kind,
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
                report_kind=r.report_kind,
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
            report_kind=r.report_kind,
            project_count=r.project_count,
        )
    )

@router.get("/resume/context/{id}", dependencies=[Depends(require_consent)])
def get_resume_context(id: int):
    """
    Return the resume template context for a report as JSON.
    Used by the frontend live HTML preview.
    """
    rm = ReportManager()
    report = rm.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _require_report_kind(report, "resume")
    return ReportExporter()._build_context(report, ConfigManager())


@router.patch("/reports/{id}/projects/{project_name}", dependencies=[Depends(require_consent)])
def patch_report_project(id: int, project_name: str, req: ReportProjectPatchRequest):
    """
    Update editable fields on a single ReportProject within a report.
    Only non-None fields are applied.
    """
    from urllib.parse import unquote
    project_name = unquote(project_name)

    rm = ReportManager()
    report = rm.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    target = next((p for p in report.projects if p.project_name == project_name), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found in report.")

    if req.project_name is not None:
        target.project_name = req.project_name
    if req.stack_languages is not None:
        target.languages = req.stack_languages
    if req.stack_frameworks is not None:
        target.frameworks = req.stack_frameworks
    if req.bullets is not None:
        target.bullets = req.bullets

    rm.update_report(report)
    return {"ok": True, "project_name": target.project_name}


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
    if not rm.delete_report(id):
        raise HTTPException(status_code=500, detail="Failed to delete report.")
    return None


@router.get("/portfolio/{id}", response_model=PortfolioResponse, dependencies=[Depends(require_consent)])
def get_portfolio(id: int):
    """Retrieve a generated portfolio report by id."""
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")
    portfolio = _build_portfolio_report(report)
    return PortfolioResponse(ok=True, portfolio=portfolio, message="Portfolio retrieved.")


@router.post("/portfolio/export", response_model=PortfolioExportResponse, dependencies=[Depends(require_consent)])
def export_portfolio(req: PortfolioExportRequest):
    """
    Export a portfolio PDF file from a report and return download info.
    """
    rm = ReportManager()
    report = rm.get_report(req.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _require_report_kind(report, "portfolio")
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


@router.post("/portfolio/{id}/edit", response_model=PortfolioResponse, dependencies=[Depends(require_consent)])
def edit_portfolio(id: int, payload: PortfolioUpdateRequest):
    """
    Edit an existing portfolio report's title and notes.
    """
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")
    if payload.title:
        report.title = payload.title.strip()
    if payload.notes is not None:
        report.notes = payload.notes
    report_manager.update_report(report)
    portfolio = _build_portfolio_report(report)
    return PortfolioResponse(ok=True, portfolio=portfolio, message="Portfolio updated.")


@router.post("/reports/{id}/portfolio-details/generate", response_model=PortfolioDetailsGenerateResponse, dependencies=[Depends(require_consent)])
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
    _require_report_kind(report, "portfolio")

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
    _require_report_kind(report, "resume")

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

@router.get("/resume/context/{id}", dependencies=[Depends(require_consent)])
def get_resume_context(id: int):
    """
    Return the resume template context for a report as JSON.
    Used by the frontend to render a live HTML preview.
    """
    rm = ReportManager()
    report = rm.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _require_report_kind(report, "resume")
    context = ReportExporter()._build_context(report, ConfigManager())
    # Convert date objects to strings so they're JSON-serialisable
    for proj in context.get("projects", []):
        pass  # dates are already formatted strings in _build_context
    return context


class ConfigSaveRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    github: str | None = None
    linkedin: str | None = None


@router.get("/resume/exports/{export_id}/download", dependencies=[Depends(require_consent)])
def download_resume(export_id: str):
    """Download a previously exported resume file."""
    out_dir = Path("resumes")
    matches = list(out_dir.glob(f"{export_id}-*.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="Export not found.")
    p = matches[0]
    return FileResponse(str(p), filename=p.name)


@router.get("/config")
def get_config():
    """Return all stored config values as a flat dict."""
    cm = ConfigManager()
    return {"ok": True, "config": cm.get_all()}


@router.post("/config")
def save_config(req: ConfigSaveRequest):
    """Persist profile fields. Only non-empty values are written."""
    cm = ConfigManager()
    for key, value in req.model_dump().items():
        if value is not None and str(value).strip():
            cm.set(key, str(value).strip())
    return {"ok": True, "config": cm.get_all()}

@router.post("/config/set")
def config_set(req: ConfigSetRequest):
    """
    Set a single config value by key. Accepts any JSON-serializable value,
    so structured data like education/experience arrays round-trip correctly.
    """
    cm = ConfigManager()
    cm.set(req.key, req.value)
    return {"ok": True, "key": req.key}
def _require_private_mode(report):
    mode = getattr(report, "portfolio_mode", "private") or "private"
    if mode != "private":
        raise HTTPException(status_code=409, detail="Portfolio is in public mode and cannot be edited.")

@router.patch("/portfolio/{id}/mode", response_model=PortfolioResponse, dependencies=[Depends(require_consent)])
def update_portfolio_mode(id: int, payload: PortfolioModeUpdateRequest):
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")

    mode = (payload.mode or "").strip().lower()
    if mode not in {"private", "public"}:
        raise HTTPException(status_code=400, detail="mode must be 'private' or 'public'.")

    report.portfolio_mode = mode
    if mode == "private":
        report.portfolio_published_at = None
    report_manager.update_report(report)
    return PortfolioResponse(ok=True, portfolio=_build_portfolio_report(report), message="Portfolio mode updated.")

@router.patch("/portfolio/{id}/projects/{project_name}", response_model=PortfolioResponse, dependencies=[Depends(require_consent)])
def update_portfolio_project_customizations(id: int, project_name: str, payload: PortfolioProjectUpdateRequest):
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")

    _require_private_mode(report)

    target = next((p for p in report.projects if p.project_name == project_name), None)
    if not target:
        raise HTTPException(status_code=404, detail="Portfolio project not found.")

    custom = dict(getattr(target, "portfolio_customizations", {}) or {})
    if payload.custom_title is not None:
        custom["custom_title"] = payload.custom_title.strip()
    if payload.custom_overview is not None:
        custom["custom_overview"] = payload.custom_overview.strip()
    if payload.custom_achievements is not None:
        custom["custom_achievements"] = [x.strip() for x in payload.custom_achievements if x and x.strip()]
    if payload.is_hidden is not None:
        custom["is_hidden"] = bool(payload.is_hidden)

    target.portfolio_customizations = custom
    report_manager.update_report(report)
    return PortfolioResponse(ok=True, portfolio=_build_portfolio_report(report), message="Portfolio project updated.")

@router.post("/portfolio/{id}/unpublish", response_model=PortfolioPublishResponse, dependencies=[Depends(require_consent)])
def unpublish_portfolio(id: int):
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")

    report.portfolio_mode = "private"
    report.portfolio_published_at = None
    report_manager.update_report(report)
    return PortfolioPublishResponse(ok=True, portfolio=_build_portfolio_report(report), message="Portfolio moved to private mode.")
@router.post("/portfolio/{id}/publish", response_model=PortfolioPublishResponse, dependencies=[Depends(require_consent)])
def publish_portfolio(id: int):
    from datetime import datetime
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    _require_report_kind(report, "portfolio")

    report.portfolio_mode = "public"
    report.portfolio_published_at = datetime.now()
    report_manager.update_report(report)
    return PortfolioPublishResponse(ok=True, portfolio=_build_portfolio_report(report), message="Portfolio published.")
