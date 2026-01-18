from fastapi import APIRouter
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager

"""For all our routes. Requirement 32, endpoints"""

router = APIRouter()

@router.post("/projects/upload")
def index():
    return {}
@router.post("/privacy-consent")
@router.get("/projects")
@router.get("/projects/{id}")
@router.get("/skills")
@router.get("/resume/{id}")
@router.post("/resume/generate")
@router.post("/resume/{id}/edit")
@router.get("/portfolio/{id}")
@router.post("/portfolio/generate")
@router.post("/portfolio/{id}/edit")
