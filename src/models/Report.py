from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
from src.models.ReportProject import ReportProject
from typing import Literal


@dataclass
class Report:
    """
    A report containing multiple project snapshots for export.
    
    Reports are "live templates" - they store which projects to include
    and how to organize them, but pull current user info (e.g. email address) at export time.
    """

    report_id: Optional[int] = None
    title: str = ""
    date_created: datetime = field(default_factory=datetime.now)
    sort_by: Literal["resume_score", "date_created", "last_modified"] = "resume_score"
    projects: List[ReportProject] = field(default_factory=list)
    notes: Optional[str] = None # For the user, e.g. "Use this one for Software Engineering roles"
    
    def __post_init__(self):
        """Sort projects and catch case where user left title empty after initialization"""
        if not self.title or not self.title.strip():
            self.title = f"Report {self.date_created.strftime('%Y-%m-%d')}"
        if self.projects:
            self._sort_projects()

    def _sort_projects(self):
        """Sort projects according to sort_by setting."""

        if self.sort_by == "resume_score":
            self.projects.sort(key=lambda p: p.resume_score, reverse=True)

        elif self.sort_by == "date_created":
            self.projects.sort(
                key=lambda p: p.date_created or datetime.min,
                reverse=True
            )

        elif self.sort_by == "last_modified":
            self.projects.sort(
                key=lambda p: p.last_modified or datetime.min,
                reverse=True
            )

    
    def add_project(self, project: "ReportProject"):
        """Add a project and re-sort"""
        self.projects.append(project)
        self._sort_projects()
    
    # done by name because ReportProjects don't have id fields. project_name is a NOT NULL field in projects table
    def remove_project(self, project_name: str) -> bool:
        """Remove project by name. Returns True if removed."""
        original_count = len(self.projects)
        self.projects = [p for p in self.projects if p.project_name != project_name]
        return len(self.projects) < original_count
    
    @property
    def project_count(self) -> int:
        """Number of projects in this report"""
        return len(self.projects)
    
    @property
    def average_score(self) -> float:
        """Average resume score across all projects"""
        if not self.projects:
            return 0.0
        return sum(p.resume_score for p in self.projects) / self.project_count
    
    @property
    def all_languages(self) -> List[str]:
        """Unique list of all languages used across projects"""
        languages = set()
        for project in self.projects:
            languages.update(project.languages)
        return sorted(languages)
    
    @property
    def all_frameworks(self) -> List[str]:
        """Unique list of all frameworks used across projects"""
        frameworks = set()
        for project in self.projects:
            frameworks.update(project.frameworks)
        return sorted(frameworks)

    def to_dict(self) -> Dict: # can't use asdict(), because we need to omit projects
        return {
            "report_id": self.report_id,
            "title": self.title,
            "date_created": self.date_created.isoformat(),
            "sort_by": self.sort_by,
            "notes": self.notes,
        }

# from_dict intentionally omitted, ReportManager will handle retrieval of Reports
    
    def __str__(self) -> str:
        """String representation of report"""

        project_names = [p.project_name for p in self.projects[:3]]
        if len(self.projects) > 3:
            projects_str = f"{', '.join(project_names)}, and {len(self.projects) - 3} more"
        elif len(self.projects) == 3:
            projects_str = f"{project_names[0]}, {project_names[1]}, and {project_names[2]}"
        elif len(self.projects) == 2:
            projects_str = f"{project_names[0]} and {project_names[1]}"
        elif len(self.projects) == 1:
            projects_str = project_names[0]
        else:
            projects_str = "none"
        
        return (
            f"Report: {self.title}\n"
            f"  Created: {self.date_created.strftime('%Y-%m-%d')}\n"
            f"  Projects Included: {projects_str}\n"
            f"  Avg Score: {self.average_score:.2f}\n"
            f"  Languages: {', '.join(self.all_languages)}\n"
            f"  Frameworks: {', '.join(self.all_frameworks)}"
        )
