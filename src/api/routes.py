from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pathlib import Path
from collections import Counter
import tempfile, shutil
from src.api.schemas import SkillsListResponse, SkillItem, PortfolioResponse, ConsentResponse, UploadProjectResponse, ProjectsListResponse, ProjectSummary, ProjectDetailResponse, ProjectDetail, TodoResponse, ResumeItemResponse
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ConsentManager import ConsentManager
from src.managers.ProjectManager import ProjectManager
from src.ZipParser import parse_zip_to_project_folders

"""For all our routes. Requirement 32, endpoints"""
router = APIRouter()

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

@router.get("/resume/{id}", response_model=ResumeItemResponse)
def get_resume(id: int):
    """
    Retrieve textual information about a project as a resume item.
    Returns the project's summary and bullet points for use in a resume.
    """
    pm = ProjectManager()
    project = pm.get(id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    return ResumeItemResponse(
        project_id=project.id,
        project_name=project.name,
        summary=project.summary or "",
        bullets=project.bullets or []
    )

@router.post("/resume/generate", response_model=TodoResponse)
def generate_resume():
    return TodoResponse(message="Resume generation not implemented yet.")

@router.post("/resume/{id}/edit", response_model=TodoResponse)
def edit_resume(id: int):
    return TodoResponse(message="Resume editing not implemented yet.")

# Note: Portfolio endpoints are placeholders.
# same idea as our resume endpoints...
# TODO: Full portfolio generation then we edit these endpoints

@router.get("/portfolio/{id}", response_model=PortfolioResponse)
def get_portfolio(id: int):
    return PortfolioResponse(
        message="Portfolio retrieval not implemented yet."
    )
@router.post("/portfolio/generate", response_model=PortfolioResponse)
def generate_portfolio():
    return PortfolioResponse(
        message="Portfolio generation not implemented yet."
    )

@router.post("/portfolio/{id}/edit")
def edit_portfolio(id: int):
    return PortfolioResponse(
        message="Portfolio editing not implemented yet."
    )
