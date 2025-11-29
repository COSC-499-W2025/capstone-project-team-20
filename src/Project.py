from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
import json

# Helper for list defaults
list_field = lambda: field(default_factory=list)


@dataclass
class Project:
    """
    Represents an analyzed project.

    - Supports badges
    - Supports code-metrics / skill dimensions (analyze_skills)
    - Serializes list fields as JSON strings for DB storage.
    """

    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    root_folder: str = ""
    num_files: int = 0
    size_kb: int = 0

    author_count: int = 0
    authors: List[str] = list_field()

    # High-level tech stack
    languages: List[str] = list_field()
    frameworks: List[str] = list_field()
    skills_used: List[str] = list_field()
    badges: List[str] = list_field()
    individual_contributions: List[str] = list_field()
    author_contributions: List[Dict[str, Any]] = list_field()
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    # Derived skill / metrics info
    # Primary languages (e.g. top by LOC, subset of `languages`)
    primary_languages: List[str] = list_field()

    # Overall code metrics
    total_loc: int = 0
    comment_ratio: float = 0.0
    test_file_ratio: float = 0.0
    avg_functions_per_file: float = 0.0
    max_function_length: int = 0

    # Skill dimensions
    testing_discipline_level: str = ""
    testing_discipline_score: float = 0.0

    documentation_habits_level: str = ""
    documentation_habits_score: float = 0.0

    modularity_level: str = ""
    modularity_score: float = 0.0

    language_depth_level: str = ""
    language_depth_score: float = 0.0

    # Timestamps
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert to a dict suitable for DB storage.

        - List fields are stored as JSON strings.
        - Datetimes are stored as ISO 8601 strings (or None).
        """
        proj_dict = asdict(self)

        # Keep author_count in sync with authors list
        proj_dict["author_count"] = len(self.authors)

        list_fields = [
            "authors",
            "languages",
            "frameworks",
            "skills_used",
            "badges",
            "individual_contributions",
            "author_contributions",
            "primary_languages",
        ]

        for field_name in list_fields:
            value = proj_dict.get(field_name, [])
            # Single JSON dump (avoid double-encoding)
            proj_dict[field_name] = json.dumps(value)

        # Datetime -> ISO string
        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict.get(field_name)
            if isinstance(value, datetime):
                proj_dict[field_name] = value.isoformat()
            else:
                proj_dict[field_name] = None if value is None else value

        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> Project:
        """
        Reconstruct a Project from a DB row dict.

        - JSON strings for list fields are decoded back to Python lists.
        - Datetime strings are parsed back into datetime objects.
        - Handles legacy double-encoded JSON safely.
        """
        proj_dict_copy = dict(proj_dict)

        list_fields = [
            "authors",
            "languages",
            "frameworks",
            "skills_used",
            "badges",
            "individual_contributions",
            "author_contributions",
            "primary_languages",
        ]

        for field_name in list_fields:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    decoded = json.loads(value)
                    # If old data was double-encoded, decoded may still be a string
                    if isinstance(decoded, str):
                        try:
                            decoded2 = json.loads(decoded)
                            decoded = decoded2
                        except json.JSONDecodeError:
                            pass
                    proj_dict_copy[field_name] = decoded
                except json.JSONDecodeError:
                    proj_dict_copy[field_name] = []
            elif value is None:
                proj_dict_copy[field_name] = []
            # if already a list, leave it as-is

        # Datetime fields
        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = datetime.fromisoformat(value)
                except ValueError:
                    proj_dict_copy[field_name] = None
            elif not isinstance(value, datetime):
                proj_dict_copy[field_name] = None

        # Filter out unknown keys (in case the DB has extra columns)
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in proj_dict_copy.items() if k in known_keys}

        project = cls(**filtered)
        project.update_author_count()
        return project

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------

    def update_author_count(self) -> None:
        """Keep author_count in sync with authors list."""
        self.author_count = len(self.authors)

    def display(self) -> None:
        """
        Basic pretty-printer used by ProjectAnalyzer.display_analysis_results().
        Formatting is kept simple so tests don't depend on specific layout.
        """
        print(f"\nProject: {self.name}")
        print(f"  Path: {self.file_path}")
        print(f"  Authors ({self.author_count}): {', '.join(self.authors) or 'N/A'}")
        print(f"  Languages: {', '.join(self.languages) or 'N/A'}")
        if self.badges:
            print(f"  Badges: {', '.join(self.badges)}")
        if self.primary_languages:
            print(f"  Primary languages: {', '.join(self.primary_languages)}")
