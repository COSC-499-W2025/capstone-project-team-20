from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional
from datetime import datetime
import json
from pathlib import Path

# Import necessary GitPython components.
from git import Repo, GitCommandError

#helper to clean things up a bit
list_field = lambda: field(default_factory=list)

@dataclass
class Project:
    """This class represents a project detected by our system."""
    id: Optional[int] = None
    name: str = ""
    # Add non-persistent fields for runtime analysis.
    # `repr=False` keeps the object representation clean.
    repo_path: Optional[Path] = field(default=None, repr=False)
    repo: Optional[Repo] = field(init=False, default=None, repr=False)
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
    collaboration_status: Literal["individual", "collaborative"] = "individual"
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def __post_init__(self):
        """
        Initializes the GitPython Repo object after the dataclass is created.
        This method is automatically called and attempts to create a `Repo`
        instance if `repo_path` is set.
        """
        if self.repo_path:
            try:
                self.repo = Repo(self.repo_path)
            except (GitCommandError, TypeError) as e:
                print(f"Warning: Could not initialize repository at {self.repo_path}. Error: {e}")
                self.repo = None

    def to_dict(self) -> dict:
        """
        Return a dict representation of Project object for DB storage.
        This method now excludes the transient `repo_path` and `repo` fields.
        """
        # Use a dict factory to filter out non-persistent fields during conversion.
        persistent_fields = {k: v for (k, v) in asdict(self).items() if k not in ["repo_path", "repo"]}

        # The existing serialization logic remains unchanged.
        for field_name in ["authors", "languages", "frameworks", "skills_used", "individual_contributions"]:
            persistent_fields[field_name] = json.dumps(persistent_fields[field_name])
        persistent_fields["author_count"] = len(self.authors)
        persistent_fields["date_created"] = self.date_created.isoformat() if self.date_created else None
        persistent_fields["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        persistent_fields["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None
        return persistent_fields

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

        # Filter out keys that are not part of the dataclass definition before instantiation.
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in proj_dict.items() if k in known_keys}

        project = cls(**filtered_dict)
        project.update_author_count()
        return project

    def update_author_count(self):
        self.author_count = len(self.authors)
