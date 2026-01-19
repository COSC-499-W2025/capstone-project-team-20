"""Tests for the resume item endpoint (Requirement #299)"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.api.api_main import app
from src.models.Project import Project


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_get_resume_item_success(client):
    """Test successful retrieval of a project's resume item information."""
    # Create a mock project with resume data
    mock_project = Project(
        id=1,
        name="Sample Portfolio Project",
        summary="Built a full-stack web application",
        bullets=["Implemented REST API with FastAPI", "Created React frontend", "Deployed to AWS"]
    )
    
    with patch("src.api.routes.ProjectManager") as mock_pm_class:
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm
        mock_pm.get.return_value = mock_project
        
        response = client.get("/resume/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["project_id"] == 1
    assert data["project_name"] == "Sample Portfolio Project"
    assert data["summary"] == "Built a full-stack web application"
    assert len(data["bullets"]) == 3
    assert "Implemented REST API with FastAPI" in data["bullets"]


def test_get_resume_item_not_found(client):
    """Test retrieval when project does not exist."""
    with patch("src.api.routes.ProjectManager") as mock_pm_class:
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm
        mock_pm.get.return_value = None
        
        response = client.get("/resume/999")
    
    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]


def test_get_resume_item_empty_bullets(client):
    """Test retrieval when project has no bullets yet."""
    mock_project = Project(
        id=2,
        name="Another Project",
        summary="A project in progress",
        bullets=[]
    )
    
    with patch("src.api.routes.ProjectManager") as mock_pm_class:
        mock_pm = MagicMock()
        mock_pm_class.return_value = mock_pm
        mock_pm.get.return_value = mock_project
        
        response = client.get("/resume/2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["bullets"] == []
    assert data["summary"] == "A project in progress"
