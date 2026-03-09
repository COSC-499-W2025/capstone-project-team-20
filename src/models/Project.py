from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import json
from src.models.ReportProject import PortfolioDetails

list_field = lambda: field(default_factory=list)


@dataclass
class Project:
    """
    This class represents a project detected by our system. 
    It is a pure data container representing a single analyzed project.

    Checklist for adding a variable to this class:
        1. If it's a List or Dict, add it to LIST_FIELDS / DICT_FIELDS
        2. Update display() to reflect new variable
        3. Update ProjectManager.py
    """

    # Declare all list-based and dict-based fields that must be serialized and de-serialized to/from JSON strings.

    LIST_FIELDS = [
        "authors",
        "languages",
        "frameworks",
        "skills_used",
        "skills_selected",
        "dependencies_list",
        "dependency_files_list",
        "build_tools",
        "readme_keywords",
        "author_contributions",
        "bullets",
    ]

    DICT_FIELDS = [
        "categories",
        "language_share",
        "portfolio_details",
        "contributor_roles",
        "individual_contributions",
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
    skills_selected: List[str] = list_field()

    # Dependency and tooling info
    dependencies_list: List[str] = list_field()
    dependency_files_list: List[str] = list_field()
    build_tools: List[str] = list_field()

    individual_contributions: Dict[str, Any] = field(default_factory=dict)
    author_contributions: List[Dict[str, Any]] = list_field()
    contributor_roles: Dict[str, Any] = field(default_factory=dict)
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    # Code metrics
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

    # Skill dimensions
    testing_discipline_level: str = ""
    testing_discipline_score: float = 0.0
    documentation_habits_level: str = ""
    documentation_habits_score: float = 0.0
    modularity_level: str = ""
    modularity_score: float = 0.0
    language_depth_level: str = ""
    language_depth_score: float = 0.0

    # Classifier output
    project_type: str = ""

    # Resume insights
    bullets: List[str] = list_field()
    summary: str = ""
    portfolio_entry: str = ""
    portfolio_details: PortfolioDetails = field(default_factory=PortfolioDetails)
    thumbnail: Optional[str] = None

    # Scoring
    resume_score: float = 0.0

    # Timestamps
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    import_batch_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        proj_dict = asdict(self)
        if isinstance(proj_dict.get("portfolio_details"), PortfolioDetails):
            proj_dict["portfolio_details"] = proj_dict["portfolio_details"].to_dict()
        for field_name in Project.LIST_FIELDS + Project.DICT_FIELDS:
            proj_dict[field_name] = json.dumps(proj_dict[field_name])
        proj_dict["author_count"] = len(self.authors)
        proj_dict["date_created"] = self.date_created.isoformat() if self.date_created else None
        proj_dict["last_modified"] = self.last_modified.isoformat() if self.last_modified else None
        proj_dict["last_accessed"] = self.last_accessed.isoformat() if self.last_accessed else None
        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> "Project":
        proj_dict_copy = proj_dict.copy()
        for field_name in Project.LIST_FIELDS:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = json.loads(value)
                except json.JSONDecodeError:
                    proj_dict_copy[field_name] = []
            elif value is None:
                proj_dict_copy[field_name] = []
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

        for field_name in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = datetime.fromisoformat(value)
                except ValueError:
                    proj_dict_copy[field_name] = None
            else:
                proj_dict_copy[field_name] = None

        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in proj_dict_copy.items() if k in known_keys}
        project = cls(**filtered_dict)
        project.update_author_count()
        return project

    def update_author_count(self):
        self.author_count = len(self.authors)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display(self) -> None:
        print(f"\n{'='*50}")
        print(f"  📁 {self.name}  (Resume Score: {self.resume_score:.2f})")
        if self.project_type:
            print(f"  🏷  Project Type: {self.project_type}")
        print(f"{'='*50}")

        # Identity & paths
        if self.file_path:
            print(f"  File Path:   {self.file_path}")
        if self.root_folder:
            print(f"  Root Folder: {self.root_folder}")

        # Authorship
        if self.authors:
            print(f"  Authors ({self.author_count}): {', '.join(self.authors)}")
        print(f"  Status: {self.collaboration_status}")

        if self.contributor_roles:
            print("\n  Contributor roles:")
            for user, info in self.contributor_roles.items():
                role = info.get("primary_role", "role_none")
                conf = info.get("confidence", 0.0)
                print(f"    - {user}: {role} ({conf:.2f})")

        # Tech stack
        if self.languages:
            print(f"\n  Languages: {', '.join(self.languages)}")
        if self.language_share:
            print("  Language share:")
            for lang, share in sorted(self.language_share.items(), key=lambda x: x[0].lower()):
                print(f"    - {lang}: {share:.1f}%")
        if self.frameworks:
            print(f"  Frameworks: {', '.join(self.frameworks)}")
        if self.skills_used:
            print(f"  Skills/tools: {', '.join(self.skills_used)}")
        if self.skills_selected:
            print(f"  Selected skills: {', '.join(self.skills_selected)}")

        # Project stats
        print(f"\n  Project stats:")
        if self.num_files:
            print(f"    - Files:    {self.num_files}")
        if self.size_kb:
            print(f"    - Size:     {self.size_kb} KB")
        if self.date_created:
            print(f"    - Created:  {self.date_created.strftime('%Y-%m-%d')}")
        if self.last_modified:
            print(f"    - Modified: {self.last_modified.strftime('%Y-%m-%d')}")

        # File categories
        if self.categories:
            print("\n  File categories:")
            for key, value in self.categories.items():
                value_str = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
                print(f"    - {key}: {value_str}")

        # Tech profile flags
        tech_flags = [
            label for flag, label in [
                (self.has_dockerfile, "Dockerfile"),
                (self.has_database,   "Database"),
                (self.has_frontend,   "Frontend"),
                (self.has_backend,    "Backend"),
                (self.has_test_files, "Tests"),
                (self.has_readme,     "README"),
            ] if flag
        ]
        if tech_flags or self.readme_keywords:
            print("\n  Tech profile:")
            if tech_flags:
                print(f"    - Flags:    {', '.join(tech_flags)}")
            if self.readme_keywords:
                print(f"    - README keywords: {', '.join(self.readme_keywords)}")

        # Dependencies & tooling
        if any([self.dependencies_list, self.dependency_files_list, self.build_tools]):
            print("\n  Dependencies & tooling:")
            if self.dependencies_list:
                preview = ", ".join(self.dependencies_list[:8])
                if len(self.dependencies_list) > 8:
                    preview += " ..."
                print(f"    - Dependencies ({len(self.dependencies_list)}): {preview}")
            if self.dependency_files_list:
                print(f"    - Dep files:  {', '.join(self.dependency_files_list)}")
            if self.build_tools:
                print(f"    - Build tools: {', '.join(self.build_tools)}")

        # Code metrics
        if any([self.total_loc, self.comment_ratio, self.test_file_ratio,
                self.avg_functions_per_file, self.max_function_length]):
            print("\n  Code metrics:")
            if self.total_loc:
                print(f"    - Total LOC:            {self.total_loc}")
            if self.comment_ratio:
                print(f"    - Comment ratio:        {self.comment_ratio:.1%}")
            if self.test_file_ratio:
                print(f"    - Test file ratio:      {self.test_file_ratio:.1%}")
            if self.avg_functions_per_file:
                print(f"    - Avg functions/file:   {self.avg_functions_per_file:.2f}")
            if self.max_function_length:
                print(f"    - Longest function:     {self.max_function_length} lines")

        # Code quality dimensions
        dims = [
            ("Testing discipline",    self.testing_discipline_level,    self.testing_discipline_score),
            ("Documentation habits",  self.documentation_habits_level,  self.documentation_habits_score),
            ("Modularity",            self.modularity_level,            self.modularity_score),
            ("Language depth",        self.language_depth_level,        self.language_depth_score),
        ]
        if any(level for _, level, _ in dims):
            print("\n  Code quality dimensions:")
            for label, level, score in dims:
                if level:
                    print(f"    - {label:<22} {level} ({score:.2f})")

        # Resume insights
        if self.bullets:
            print("\n  Resume bullets:")
            for b in self.bullets:
                print(f"    • {b}")
        if self.summary:
            print(f"\n  Summary:\n    {self.summary}")
        if self.portfolio_entry:
            print(f"\n  Portfolio entry:\n    {self.portfolio_entry}")

        print()
