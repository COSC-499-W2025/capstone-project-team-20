from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import json

# This helper remains useful for creating default lists.
list_field = lambda: field(default_factory=list)

@dataclass
class Project:
    """
    This class represents a project detected by our system. It is a pure data
    container with no external dependencies or file system interactions.
    """
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
    author_contributions: List[Dict[str, Any]] = list_field()
    collaboration_status: Literal["individual", "collaborative"] = "individual"
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the Project object for database storage.
        This method serializes list and datetime fields into JSON-compatible formats.
        """
        proj_dict = asdict(self)

        # Serialize list-based and dict-based fields to JSON strings.
        for field_name in ["authors", "languages", "frameworks", "skills_used", "individual_contributions", "author_contributions"]:
            proj_dict[field_name] = json.dumps(proj_dict[field_name])

        # Ensure author_count is consistent with the authors list.
        proj_dict["author_count"] = len(self.authors)

        # Serialize datetime objects to ISO 8601 format strings.
        proj_dict["date_created"] = self.date_created.isoformat() if self.date_created else None
        proj_dict["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        proj_dict["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None
        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> Project:
        """
        Reconstructs a Project object from a dictionary, typically from a database record.
        This method deserializes JSON strings back into their original Python types.
        """
        # Create a copy to avoid modifying the original dictionary.
        proj_dict_copy = proj_dict.copy()

        # Deserialize JSON strings back into lists or dicts.
        for field_name in ["authors", "languages", "frameworks", "skills_used", "individual_contributions", "author_contributions"]:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                proj_dict_copy[field_name] = json.loads(value)
            elif value is None:
                proj_dict_copy[field_name] = []

        # Deserialize ISO 8601 strings back into datetime objects.
        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                proj_dict_copy[field_name] = datetime.fromisoformat(value)
            else:
                proj_dict_copy[field_name] = None

        # Ensure only known fields are passed to the constructor.
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in proj_dict_copy.items() if k in known_keys}

        project = cls(**filtered_dict)
        project.update_author_count()
        return project

    def update_author_count(self):
        """A helper method to ensure the author_count is always in sync."""
        self.author_count = len(self.authors)
