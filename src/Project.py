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
    
    Checklist for adding a variable to this class:
        1. if that variable is a List or a Dict, it must be added to the list_fields section in to_dict() and from_dict() 
        2. the display() method must be updated to reflect the addition of this variable
        3. make the necessary changes for your new variable in ProjectManager.py
    """
    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    root_folder: str = ""
    num_files: int = 0
    size_kb: int = 0
    categories: Dict[str, Any] = field(default_factory=dict)
    author_count: int = 0
    authors: List[str] = list_field()

    # High-level tech stack
    languages: List[str] = list_field()
    frameworks: List[str] = list_field()
    skills_used: List[str] = list_field()
    individual_contributions: List[str] = list_field()
    author_contributions: List[Dict[str, Any]] = list_field()
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    # === New: derived skill/metrics info ===
    # Primary languages (e.g. top by LOC, subset of `languages`)
    primary_languages: List[str] = list_field()

    # Overall code metrics (from CodeMetricsAnalyzer.summarize()["overall"])
    total_loc: int = 0
    comment_ratio: float = 0.0
    test_file_ratio: float = 0.0
    avg_functions_per_file: float = 0.0
    max_function_length: int = 0

    # Skill dimensions (from SkillAnalyzer._compute_dimensions)
    testing_discipline_level: str = ""       # "strong" | "good" | "ok" | "needs_improvement"
    testing_discipline_score: float = 0.0

    documentation_habits_level: str = ""
    documentation_habits_score: float = 0.0

    modularity_level: str = ""
    modularity_score: float = 0.0

    language_depth_level: str = ""
    language_depth_score: float = 0.0

    # Resume Insights - generated from ResumeInsightsGenerator
    bullets: List[str] = list_field()
    summary: str = ""
    # Scoring for ranking projects against one another
    resume_score: float = 0.0

    # Timestamps
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the Project object for database storage.
        This method serializes list and datetime fields into JSON-compatible formats.
        """
        proj_dict = asdict(self)

        # Declare all list-based and dict-based fields that must be serialized to JSON strings.
        list_fields = [
            "authors",
            "languages",
            "frameworks",
            "skills_used",
            "individual_contributions",
            "author_contributions",
            "primary_languages",
            "bullets",
            "categories"
        ]
        for field_name in list_fields:
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

        # Declare all list-based and dict-based fields that must be de-serialized from JSON strings.
        list_fields = [
            "authors",
            "languages",
            "frameworks",
            "skills_used",
            "individual_contributions",
            "author_contributions",
            "primary_languages",
            "bullets",
            "categories"
        ]
        for field_name in list_fields:
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

    def display(self) -> None:
        """Print the project details to the console."""
        print(f"\n{'='*50}")
        print(f"  📁 {self.name}  (Resume Score: {self.resume_score:.2f})")
        print(f"{'='*50}")
        if self.file_path:
            print(f"  File Path: {self.file_path}")
        if self.authors:
            print(f"  Authors ({self.author_count}): {', '.join(self.authors)}")
        print(f"  Status: {self.collaboration_status}")

        # High-level tech stack
        if self.languages:
            print(f"  Languages: {', '.join(self.languages)}")
        if self.primary_languages:
            print(f"  Primary languages (by LOC): {', '.join(self.primary_languages)}")
        if self.frameworks:
            print(f"  Frameworks: {', '.join(self.frameworks)}")
        if self.skills_used:
            print(f"  Other skills/tools: {', '.join(self.skills_used)}")

        # Basic project stats
        if self.num_files:
            print(f"  Files: {self.num_files}")
        if self.size_kb:
            print(f"  Size: {self.size_kb} KB")
        if self.date_created:
            print(f"  Created: {self.date_created.strftime('%Y-%m-%d')}")
        if self.last_modified:
            print(f"  Modified: {self.last_modified.strftime('%Y-%m-%d')}")

        # Code metrics (populated by Analyze Skills)
        has_metrics = any([
            self.total_loc,
            self.comment_ratio,
            self.test_file_ratio,
            self.avg_functions_per_file,
            self.max_function_length,
        ])
        if has_metrics:
            print("\n  Code metrics:")
            if self.total_loc:
                print(f"    - Total LOC: {self.total_loc}")
            if self.comment_ratio:
                print(f"    - Comment ratio: {self.comment_ratio:.1%}")
            if self.test_file_ratio:
                print(f"    - Test file ratio: {self.test_file_ratio:.1%}")
            if self.avg_functions_per_file:
                print(f"    - Avg functions/file: {self.avg_functions_per_file:.2f}")
            if self.max_function_length:
                print(f"    - Longest function (lines): {self.max_function_length}")

        # Skill dimensions (high-level “quality” view)
        dims = [
            ("Testing discipline", self.testing_discipline_level, self.testing_discipline_score),
            ("Documentation habits", self.documentation_habits_level, self.documentation_habits_score),
            ("Modularity", self.modularity_level, self.modularity_score),
            ("Language depth", self.language_depth_level, self.language_depth_score),
        ]
        if any(level for _, level, _ in dims):
            print("\n  Code quality dimensions:")
            for label, level, score in dims:
                if level:
                    print(f"    - {label}: {level} (score {score:.2f})")
        if self.bullets:
            for b in self.bullets:
                print(f" • {b}")
        if self.summary:
            print(self.summary)

        print()
