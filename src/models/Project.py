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
    """

    LIST_FIELDS = [
        "authors", "languages", "frameworks", "skills_used",
        "individual_contributions", "author_contributions", "bullets",
        "dependencies_list", "dependency_files_list", "build_tools", "readme_keywords"
    ]
    DICT_FIELDS = [
        "categories", "language_share"
    ]

    # --- Project Core Fields ---
    id: Optional[int] = None
    name: str = ""
    file_path: str = ""
    root_folder: str = ""
    num_files: int = 0
    size_kb: int = 0
    categories: Dict[str, Any] = field(default_factory=dict)
    author_count: int = 0
    authors: List[str] = list_field()

    # --- Tech Stack ---
    languages: List[str] = list_field()
    language_share: Dict[str, float] = field(default_factory=dict)
    frameworks: List[str] = list_field()
    skills_used: List[str] = list_field()
    dependencies_list: List[str] = list_field()
    dependency_files_list: List[str] = list_field()
    build_tools: List[str] = list_field()

    # --- Contribution & Collaboration ---
    individual_contributions: List[str] = list_field()
    author_contributions: List[Dict[str, Any]] = list_field()
    collaboration_status: Literal["individual", "collaborative"] = "individual"

    # --- Code Metrics ---
    total_loc: int = 0
    comment_ratio: float = 0.0
    test_file_ratio: float = 0.0
    avg_functions_per_file: float = 0.0
    max_function_length: int = 0

    # --- Tech Profile ---
    has_dockerfile: bool = False
    has_database: bool = False
    has_frontend: bool = False
    has_backend: bool = False
    has_test_files: bool = False
    has_readme: bool = False
    readme_keywords: List[str] = list_field()

    # --- Skill Dimensions (Scores) ---
    testing_discipline_level: str = ""
    testing_discipline_score: float = 0.0
    documentation_habits_level: str = ""
    documentation_habits_score: float = 0.0
    modularity_level: str = ""
    modularity_score: float = 0.0
    language_depth_level: str = ""
    language_depth_score: float = 0.0
    resume_score: float = 0.0

    # --- Generated Insights ---
    bullets: List[str] = list_field()
    summary: str = ""
    portfolio_details: PortfolioDetails = field(default_factory=PortfolioDetails)

    # --- Timestamps ---
    date_created: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the Project object for database storage.
        """
        proj_dict = asdict(self)

        for field_name in self.LIST_FIELDS + self.DICT_FIELDS:
            if field_name in proj_dict:
                proj_dict[field_name] = json.dumps(proj_dict[field_name])

        proj_dict['portfolio_details'] = json.dumps(self.portfolio_details.to_dict()) if self.portfolio_details else None

        for dt_field in ["date_created", "last_modified", "last_accessed"]:
            if proj_dict[dt_field]:
                proj_dict[dt_field] = proj_dict[dt_field].isoformat()

        return proj_dict

    @classmethod
    def from_dict(cls, proj_dict: dict) -> "Project":
        """
        Reconstructs a Project object from a dictionary.
        """
        proj_dict_copy = proj_dict.copy()

        for field_name in cls.LIST_FIELDS + cls.DICT_FIELDS:
            value = proj_dict_copy.get(field_name)
            if isinstance(value, str):
                try:
                    proj_dict_copy[field_name] = json.loads(value)
                except json.JSONDecodeError:
                    proj_dict_copy[field_name] = [] if field_name in cls.LIST_FIELDS else {}

        portfolio_data = proj_dict_copy.get("portfolio_details")
        if isinstance(portfolio_data, str):
            try:
                portfolio_data = json.loads(portfolio_data)
            except json.JSONDecodeError:
                portfolio_data = {}

        if isinstance(portfolio_data, dict):
            proj_dict_copy["portfolio_details"] = PortfolioDetails.from_dict(portfolio_data)
        else:
            proj_dict_copy["portfolio_details"] = PortfolioDetails()

        for dt_field in ["date_created", "last_modified", "last_accessed"]:
            value = proj_dict_copy.get(dt_field)
            if isinstance(value, str):
                try:
                    proj_dict_copy[dt_field] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    proj_dict_copy[dt_field] = None

        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in proj_dict_copy.items() if k in known_keys}

        return cls(**filtered_dict)

    def display(self) -> None:
        """Print the project details to the console."""
        print(f"\n{'='*50}")
        print(f"  📁 {self.name}  (Resume Score: {self.resume_score:.2f})")
        print(f"{'='*50}")
        if self.file_path: print(f"  File Path: {self.file_path}")
        if self.authors: print(f"  Authors ({len(self.authors)}): {', '.join(self.authors)}")
        print(f"\n  --- Tech Stack ---")
        if self.languages: print(f"  Languages: {', '.join(self.languages)}")
        if self.frameworks: print(f"  Frameworks: {', '.join(self.frameworks)}")
        if self.skills_used: print(f"  Skills/Tools: {', '.join(self.skills_used)}")
        print(f"\n  --- Generated Insights ---")
        if self.bullets:
            print("  Resume Bullets:")
            for b in self.bullets:
                print(f"    • {b}")
        if self.summary:
            print(f"\n  Resume Summary: {self.summary}")
        print("\n  (Structured portfolio details are generated but not displayed here.)")
        print()
