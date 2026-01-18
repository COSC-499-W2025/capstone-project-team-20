from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pathlib import Path
import tempfile, shutil
from src.api.schemas import ConsentResponse, UploadProjectResponse, ProjectsListResponse, ProjectSummary, ProjectDetailResponse, ProjectDetail
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

@router.get("/skills")
def get_skills_list():

@router.get("/resume/{id}")
def get_resume(id: int):

@router.post("/resume/generate")
def generate_resume():

@router.post("/resume/{id}/edit")
def edit_resume(id: int):

@router.get("/portfolio/{id}")
def get_portfolio(id: int):

@router.post("/portfolio/generate")
def generate_portfolio():

@router.post("/portfolio/{id}/edit")
def edit_portfolio(id: int):
