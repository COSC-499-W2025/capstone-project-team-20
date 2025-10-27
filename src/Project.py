from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional
from datetime import datetime
import json

#helper to clean things up a bit
list_field = lambda: field(default_factory=list)

@dataclass
class Project:
    """This class represents a project detected by our system."""
    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    root_folder: str = ""
    num_files: int = 0
    size_kb: int = 0
    author_count: int = 0
    authors: List[str] = list_field()
    languages: List[str] = list_field()
    frameworks: List[str] = list_field()
    skills_used: List[str] = list_field()
    individual_contributions: List[str] = list_field()
    collaboration_status: Literal["INDIVIDUAL", "COLLABORATIVE"] = "INDIVIDUAL"
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Return a dict representation of Project object for DB storage."""
        proj_dict = asdict(self)

        for field_name in ["authors", "languages", "frameworks", "skills_used", "individual_contributions"]:
            proj_dict[field_name] = json.dumps(getattr(self, field_name))
        proj_dict["author_count"] = len(self.authors)
        proj_dict["date_created"] = self.date_created.isoformat() if self.date_created else None
        proj_dict["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        proj_dict["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None
        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> Project:
        """Return reconstructed Project object from DB."""
        proj_dict = proj_dict.copy()

        for field_name in ["authors", "languages", "frameworks", "skills_used", "individual_contributions"]:
            value = proj_dict.get(field_name, "[]")
            if isinstance(value, str):
                proj_dict[field_name] = json.loads(value)
            else:
                proj_dict[field_name] = value

        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict.get(field_name)
            if isinstance(value, str):
                proj_dict[field_name] = datetime.fromisoformat(value)
            else:
                proj_dict[field_name] = value
        project = cls(**proj_dict)
        project.update_author_count()
        return project
    
    def update_author_count(self):
        self.author_count = len(self.authors)

        

