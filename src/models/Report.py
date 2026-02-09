from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from src.models.ReportProject import ReportProject
from typing import Literal

@dataclass
class Report:
    """A report containing multiple project snapshots for export."""
    id: Optional[int] = None
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    sort_by: Literal["resume_score", "date_created", "last_modified"] = "resume_score"
    projects: List[ReportProject] = field(default_factory=list, compare=False, repr=False)
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.title or not self.title.strip():
            self.title = f"Report {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        if self.projects:
            self._sort_projects()

    def _sort_projects(self):
        if self.sort_by == "resume_score":
            self.projects.sort(key=lambda p: p.resume_score, reverse=True)
        elif self.sort_by == "date_created":
            self.projects.sort(key=lambda p: p.date_created or datetime.min, reverse=True)
        elif self.sort_by == "last_modified":
            self.projects.sort(key=lambda p: p.last_modified or datetime.min, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Report's main fields. The 'projects' list is handled separately."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "sort_by": self.sort_by,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Reconstructs a base Report object from a database record."""
        created_at_val = datetime.now()
        created_at_str = data.get('created_at')
        if isinstance(created_at_str, str):
            try:
                created_at_val = datetime.fromisoformat(created_at_str)
            except ValueError:
                pass

        return cls(
            id=data.get("id"),
            title=data.get("title"),
            created_at=created_at_val,
            sort_by=data.get("sort_by", "resume_score"),
            notes=data.get("notes"),
            projects=[] # The manager will populate this list separately.
        )
