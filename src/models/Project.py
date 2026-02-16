from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import json
from src.models.ReportProject import PortfolioDetails

# This helper remains useful for creating default lists.
list_field = lambda: field(default_factory=list)


@dataclass
class Project:
    """
    This class represents a project detected by our system. It is a pure data
    container with no external dependencies or file system interactions.

    Checklist for adding a variable to this class:
        1. if that variable is a List or a Dict, it must be added to class-level LIST_FIELDS / DICT_FIELDS
        2. the display() method must be updated to reflect the addition of this variable
        3. make the necessary changes for your new variable in ProjectManager.py
    """

    # Declare all list-based and dict-based fields that must be serialized and de-serialized to/from JSON strings.

    LIST_FIELDS = [
            "authors",
            "languages",
            "frameworks",
            "skills_used",
            "individual_contributions",
            "author_contributions",
            "bullets"
    ]

    DICT_FIELDS = [
            "categories",
            "language_share",
            "portfolio_details"
    ]

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
    language_share: Dict[str, float] = field(default_factory=dict)
    frameworks: List[str] = list_field()
    skills_used: List[str] = list_field()

    # New: dependency and tooling info
    dependencies_list: List[str] = list_field()
    dependency_files_list: List[str] = list_field()
    build_tools: List[str] = list_field()

    individual_contributions: List[str] = list_field()
    author_contributions: List[Dict[str, Any]] = list_field()
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    # Overall code metrics (from CodeMetricsAnalyzer.summarize()["overall"])
    total_loc: int = 0
    comment_ratio: float = 0.0
    test_file_ratio: float = 0.0
    avg_functions_per_file: float = 0.0
    max_function_length: int = 0

    # Tech-profile flags
    has_dockerfile: bool = False
    has_database: bool = False
    has_frontend: bool = False
    has_backend: bool = False
    has_test_files: bool = False
    has_readme: bool = False
    readme_keywords: List[str] = list_field()

    # Skill dimensions ...
    testing_discipline_level: str = ""
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
    portfolio_entry: str = ""
    portfolio_details: PortfolioDetails = field(default_factory=PortfolioDetails)
    thumbnail: Optional[str] = None # Path to thumbnail image

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

        if isinstance(proj_dict.get("portfolio_details"), PortfolioDetails):
            proj_dict["portfolio_details"] = proj_dict["portfolio_details"].to_dict()

        # Declare all list-based and dict-based fields that must be serialized to JSON strings.

        for field_name in Project.LIST_FIELDS + Project.DICT_FIELDS:
            proj_dict[field_name] = json.dumps(proj_dict[field_name])

        # Ensure author_count is consistent with the authors list.
        proj_dict["author_count"] = len(self.authors)

        # Serialize datetime objects to ISO 8601 format strings.
        proj_dict["date_created"] = self.date_created.isoformat() if self.date_created else None
        proj_dict["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        proj_dict["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None

        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> "Project":
        """
        Reconstructs a Project object from a dictionary, typically from a database record.
        This method deserializes JSON strings back into their original Python types.
        """
        proj_dict_copy = proj_dict.copy()

        #de-serialize lists from JSON strings
        for field_name in Project.LIST_FIELDS:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = json.loads(value)
                except json.JSONDecodeError:
                    proj_dict_copy[field_name] = {} if field_name == "categories" else []
            elif value is None:
                proj_dict_copy[field_name] = {} if field_name == "categories" else []

        #de-serialize dicts from JSON strings
        for field_name in Project.DICT_FIELDS:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                proj_dict_copy[field_name] = json.loads(value)
            elif value is None:
                proj_dict_copy[field_name] = {}

        if isinstance(proj_dict_copy.get("portfolio_details"), dict):
            proj_dict_copy["portfolio_details"] = PortfolioDetails.from_dict(proj_dict_copy["portfolio_details"])
        else:
            proj_dict_copy["portfolio_details"] = PortfolioDetails()

        # Deserialize ISO 8601 strings back into datetime objects.
        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = datetime.fromisoformat(value)
                except ValueError:
                    proj_dict_copy[field_name] = None
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
        if self.root_folder:
            print(f"  File Path: {self.root_folder}")
        if self.authors:
            print(f"  Authors ({self.author_count}): {', '.join(self.authors)}")
        print(f"  Status: {self.collaboration_status}")

        # High-level tech stack
        if self.languages:
            print(f"  Languages: {', '.join(self.languages)}")
        if self.language_share:
            print("  Language share:")
            for lang, share in sorted(self.language_share.items(), key=lambda x: x[0].lower()):
                print(f"    - {lang}: {share:.1f}%")

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

        # Categories (if populated by metadata extractor / CLI)
        if self.categories:
            print("\n  Categories:")
            for key, value in self.categories.items():
                if isinstance(value, list):
                    value_str = ", ".join(map(str, value))
                else:
                    value_str = str(value)
                print(f"    - {key}: {value_str}")

        # Tech/profile flags (Docker, DB, frontend/backend, tests, README)
        tech_flags = []
        if self.has_dockerfile:
            tech_flags.append("Dockerfile")
        if self.has_database:
            tech_flags.append("Database")
        if self.has_frontend:
            tech_flags.append("Frontend")
        if self.has_backend:
            tech_flags.append("Backend")
        if self.has_test_files:
            tech_flags.append("Tests")
        if self.has_readme:
            tech_flags.append("README")

        if tech_flags or self.readme_keywords:
            print("\n  Tech/profile flags:")
            if tech_flags:
                print(f"    - Flags: {', '.join(tech_flags)}")
            if self.readme_keywords:
                print(f"    - README keywords: {', '.join(self.readme_keywords)}")

        # Dependencies & tooling
        has_dep_info = any([self.dependencies_list,
                            self.dependency_files_list,
                            self.build_tools])
        if has_dep_info:
            print("\n  Dependencies & tooling:")
            if self.dependencies_list:
                deps_preview = ", ".join(self.dependencies_list[:8])
                if len(self.dependencies_list) > 8:
                    deps_preview += " ..."
                print(f"    - Dependencies ({len(self.dependencies_list)}): {deps_preview}")
            if self.dependency_files_list:
                print(f"    - Dependency files: {', '.join(self.dependency_files_list)}")
            if self.build_tools:
                print(f"    - Build tools: {', '.join(self.build_tools)}")

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

        # Resume insights
        if self.bullets:
            print("\n  Resume insights:")
            for b in self.bullets:
                print(f"    • {b}")
        if self.summary:
            print(f"\n  Summary:\n    {self.summary}")
        if self.portfolio_entry:
            print(f"\n  Portfolio Entry:\n    {self.portfolio_entry}")

        print()
