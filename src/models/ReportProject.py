"""
ReportProject Model

Lightweight snapshot of a project for report generation.
Captures only what's needed for resume/portfolio exports.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from datetime import datetime
import json


@dataclass
class PortfolioDetails:
    """Structured data for a single portfolio project entry."""
    project_name: str = ""
    role: str = ""
    timeline: str = ""
    technologies: str = ""
    overview: str = ""
    achievements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "role": self.role,
            "timeline": self.timeline,
            "technologies": self.technologies,
            "overview": self.overview,
            "achievements": self.achievements,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortfolioDetails":
        return cls(**data)


@dataclass
class ReportProject:
    """
    Lightweight project snapshot for reports.

    Stores only essential fields needed for resume generation,
    keeping reports lean while preserving key information.
    """

    project_name: str
    resume_score: float = 0.0

    # Resume-specific fields
    bullets: List[str] = field(default_factory=list)
    summary: str = ""

    portfolio_details: PortfolioDetails = field(default_factory=PortfolioDetails)

    # Common fields
    languages: List[str] = field(default_factory=list)
    language_share: Dict[str, float] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)

    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    @classmethod
    def from_project(cls, project) -> "ReportProject":
        """
        Create a ReportProject from a full Project object.
        Extracts only the fields needed for reports.
        """
        return cls(
            project_name=getattr(project, "name", "") or "",
            resume_score=float(getattr(project, "resume_score", 0.0) or 0.0),
            bullets=list(getattr(project, "bullets", []) or []),
            summary=getattr(project, "summary", "") or "",
            portfolio_details=getattr(project, "portfolio_details", PortfolioDetails()),
            languages=list(getattr(project, "languages", []) or []),
            language_share=dict(getattr(project, "language_share", {}) or {}),
            frameworks=list(getattr(project, "frameworks", []) or []),
            date_created=getattr(project, "date_created", None),
            last_modified=getattr(project, "last_modified", None),
            collaboration_status=(
                getattr(project, "collaboration_status", "individual")
                if getattr(project, "collaboration_status", None) in ["individual", "collaborative"]
                else "individual"
            ),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "project_name": self.project_name,
            "resume_score": self.resume_score,
            "bullets": self.bullets,
            "summary": self.summary,
            "portfolio_details": self.portfolio_details.to_dict(),
            "languages": self.languages,
            "language_share": self.language_share,
            "frameworks": self.frameworks,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "collaboration_status": self.collaboration_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReportProject":
        """Create ReportProject from dictionary"""
        data = data.copy()
        data.pop('id', None)
        data.pop('report_id', None)

        # --- THIS IS THE FIX ---
        # Handle deserialization for all complex fields, including the missing portfolio_details
        for key in ['bullets', 'languages', 'language_share', 'frameworks', 'portfolio_details']:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except (json.JSONDecodeError, TypeError):
                    data[key] = [] if key in ['bullets', 'languages', 'frameworks'] else {}

        if "date_created" in data and data["date_created"]:
            try:
                data["date_created"] = datetime.fromisoformat(data["date_created"])
            except (ValueError, TypeError):
                data["date_created"] = None
        if "last_modified" in data and data["last_modified"]:
            try:
                data["last_modified"] = datetime.fromisoformat(data["last_modified"])
            except (ValueError, TypeError):
                data["last_modified"] = None

        if "portfolio_details" in data and isinstance(data["portfolio_details"], dict):
            data["portfolio_details"] = PortfolioDetails.from_dict(data["portfolio_details"])
        else:
            data["portfolio_details"] = PortfolioDetails()

        return cls(**data)

    def get_primary_language(self) -> str:
        if not self.language_share:
            return self.languages[0] if self.languages else "N/A"
        return max(self.language_share.items(), key=lambda x: x[1])[0]

    def get_tech_stack_display(self) -> str:
        parts = []
        if self.languages:
            parts.append(", ".join(self.languages))
        if self.frameworks:
            parts.append(", ".join(self.frameworks))
        return ", ".join(parts) if parts else "N/A"

    def __str__(self) -> str:
        return f"{self.project_name} (Score: {self.resume_score:.2f})"
