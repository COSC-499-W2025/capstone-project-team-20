from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from datetime import datetime
import json

@dataclass
class Project:
    """This class represents a project detected by our system."""
    id: Optional[int] = None
    name: str = ""
    root_folder: str = ""
    num_files: int = 0
    size: int = 0
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    skills_used: List[str] = field(default_factory=list)
    individual_contributions: List[str] = field(default_factory=list)
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Return a dict representation of Project object for DB storage."""
        proj_dict = asdict(self)
        proj_dict["languages"] = json.dumps(self.languages)
        proj_dict["frameworks"] = json.dumps(self.frameworks)
        proj_dict["skills_used"] = json.dumps(self.skills_used)
        proj_dict["individual_contributions"] = json.dumps(self.individual_contributions)
        proj_dict["date_created"] = self.date_created.isoformat() if self.date_created else None
        proj_dict["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        proj_dict["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None
        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> Project:
        """Return reconstructed Project object from DB."""
        proj_dict = proj_dict.copy()
        for field_name in ["languages", "frameworks", "skills_used", "individual_contributions"]:
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

        return cls(**proj_dict)

