from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pathlib import Path
from collections import Counter
import tempfile, shutil
from src.api.schemas import SkillsListResponse, SkillItem, PortfolioResponse, ConsentResponse, UploadProjectResponse, ProjectsListResponse, ProjectSummary, ProjectDetailResponse, ProjectDetail, TodoResponse, PortfolioGenerateRequest, PortfolioGenerateResponse, PortfolioUpdateRequest, PortfolioReport, PortfolioProject, PortfolioDetailsResponse
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ConsentManager import ConsentManager
from src.managers.ProjectManager import ProjectManager
from src.managers.ReportManager import ReportManager
from src.exporters.ReportExporter import ReportExporter
from src.ZipParser import parse_zip_to_project_folders

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

@router.post("/projects/upload", response_model=UploadProjectResponse, status_code=status.HTTP_201_CREATED)
def upload_project(zip_file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(zip_file.file, tmp)

    root_folders = parse_zip_to_project_folders(str(tmp_path))
    if not root_folders:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Zip parsed no projects (invalid or empty zip.)")
    analyzer = ProjectAnalyzer(ConfigManager(), root_folders, tmp_path)
    created_projects = analyzer.initialize_projects()

    tmp_path.unlink(missing_ok=True)

    return UploadProjectResponse(
        projects=[ProjectSummary(id=p.id, name=p.name) for p in created_projects]
    )

@router.post("/privacy-consent", response_model=ConsentResponse)
def upload_consent(consent: bool):
    cm = ConsentManager()
    cm.set_consent(consent)
    return ConsentResponse(consent=consent)

@router.get("/projects", response_model=ProjectsListResponse)
def get_list_projects():
    pm = ProjectManager()
    projects = pm.get_all()
    return ProjectsListResponse(
        projects=[ProjectSummary(id=p.id, name=p.name) for p in projects]
    )

@router.get("/projects/{id}", response_model=ProjectDetailResponse)
def get_project(id: int):
    pm = ProjectManager()
    project = pm.get(id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ProjectDetailResponse(
        project=ProjectDetail(**project.__dict__)
    )

@router.get("/skills", response_model=SkillsListResponse)
def get_skills_list():
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

# Note: Resume endpoints are placeholders.
# The system only currently generates resume insights (As of Jan 18)
# TODO: Full resume generation then we edit these endpoints

@router.get("/resume/{id}", response_model=TodoResponse)
def get_resume(id: int):
    return TodoResponse(message="Resume retrieval not implemented yet.")

@router.post("/resume/generate", response_model=TodoResponse)
def generate_resume():
    return TodoResponse(message="Resume generation not implemented yet.")

@router.post("/resume/{id}/edit", response_model=TodoResponse)
def edit_resume(id: int):
    return TodoResponse(message="Resume editing not implemented yet.")

@router.get("/portfolio/{id}", response_model=PortfolioResponse)
def get_portfolio(id: int):
    report_manager = ReportManager()
    report = report_manager.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    portfolio = _build_portfolio_report(report)
    return PortfolioResponse(ok=True, portfolio=portfolio, message="Portfolio retrieved.")

@router.post("/portfolio/generate", response_model=PortfolioGenerateResponse)
def generate_portfolio(payload: PortfolioGenerateRequest):
    report_manager = ReportManager()
    report = report_manager.get_report(payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Portfolio report not found.")
    filename = payload.output_filename or f"{report.title.replace(' ', '_').lower()}_portfolio.pdf"
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    output_path = str(Path("portfolios") / filename)
    exporter = ReportExporter()
    exporter.export_to_pdf(report=report, config_manager=ConfigManager(), output_path=output_path, template="portfolio")
    return PortfolioGenerateResponse(ok=True, report_id=report.id, output_path=output_path, message="Portfolio generated.")

@router.post("/portfolio/{id}/edit", response_model=PortfolioResponse)
def edit_portfolio(id: int, payload: PortfolioUpdateRequest):
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
