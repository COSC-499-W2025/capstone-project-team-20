from datetime import datetime
from typing import Dict, Any, List
from src.models.ReportProject import PortfolioDetails


class PortfolioGenerator:
    """
    Generates structured portfolio entries for projects.
    """

    def __init__(
        self,
        metadata: Dict,
        categorized_files: Dict,
        language_share: Dict,
        project: Any,
        language_list: List[str],
    ):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list

    def generate_portfolio_details(self) -> PortfolioDetails:
        code_files, doc_files, test_files, _ = self._get_category_counts()
        total_files = sum((self.categorized_files or {}).values())

        days = self._compute_days()
        duration_str = self._format_duration(days)
        langs = ", ".join(self.language_list) if self.language_list else "multiple languages"

        team_count = self._resolve_team_count()
        contributor_roles = self._build_contributor_roles()
        role = self._select_project_role(team_count, contributor_roles)

        if team_count > 1:
            collaboration_line = f"Built collaboratively by a team of {team_count} contributors."
        else:
            collaboration_line = "Developed independently."

        overview = (
            f"This project was implemented using {langs}. "
            f"It includes {total_files} files with {code_files} source modules, "
            f"{test_files} test files, and {doc_files} documentation files. "
            f"{collaboration_line}"
        )

        key_points = self._build_key_contributions(
            langs=langs,
            code_files=code_files,
            test_files=test_files,
            doc_files=doc_files,
            team_count=team_count,
        )

        project_name = getattr(self.project, "name", "Project")

        return PortfolioDetails(
            project_name=project_name,
            role=role,
            timeline=duration_str,
            technologies=langs,
            overview=overview,
            achievements=key_points,
            contributor_roles=contributor_roles,
        )

    def _build_key_contributions(
        self,
        langs: str,
        code_files: int,
        test_files: int,
        doc_files: int,
        team_count: int,
    ) -> List[str]:
        points: List[str] = []

        points.append(f"Implemented project functionality using {langs} across {code_files} source files.")

        if test_files > 0 and doc_files > 0:
            points.append(f"Maintained {test_files} test files and {doc_files} documentation files.")
        elif test_files > 0:
            points.append(f"Maintained {test_files} test files to support quality checks.")
        elif doc_files > 0:
            points.append(f"Maintained {doc_files} documentation files for maintainability.")
        else:
            points.append("Maintained project structure and code organization.")

        if team_count > 1:
            points.append("Collaborated with team members through shared repository workflows.")
        else:
            points.append("Handled implementation and maintenance responsibilities independently.")

        return points[:3]

    def _resolve_team_count(self) -> int:
        authors = list(getattr(self.project, "authors", []) or [])
        explicit_author_count = int(getattr(self.project, "author_count", 0) or 0)

        if authors:
            return max(len(authors), explicit_author_count)
        if explicit_author_count > 0:
            return explicit_author_count

        status = getattr(self.project, "collaboration_status", "individual")
        return 2 if status == "collaborative" else 1

    def _get_category_counts(self) -> tuple[int, int, int, int]:
        counts = self.categorized_files or {}
        code_files = counts.get("code", 0)
        doc_files = counts.get("docs", 0)
        test_files = counts.get("test", 0) or counts.get("tests", 0)
        config_files = counts.get("config", 0)
        return code_files, doc_files, test_files, config_files

    def _compute_days(self) -> int:
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")
        if not start or not end:
            return 0
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d")
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d")
        return max((end - start).days, 0)

    def _format_duration(self, days: int) -> str:
        if days <= 0:
            return "N/A"
        if days < 30:
            return f"{days} days"
        months, rem = divmod(days, 30)
        if rem == 0:
            return f"{months} month" + ("s" if months > 1 else "")
        return f"{months} month" + ("s" if months > 1 else "") + f" and {rem} days"

    def _pretty_role(self, role_key: str) -> str:
        if not role_key or role_key in ("role_none", "none"):
            return "None"
        role_key = role_key.replace("role_", "")
        mapping = {
            "devops": "DevOps",
            "qa": "QA",
            "backend": "Backend",
            "frontend": "Frontend",
            "docs": "Documentation",
            "fullstack": "Fullstack",
            "tech_lead": "Tech Lead",
        }
        return mapping.get(role_key, role_key.replace("_", " ").title())

    def _build_contributor_roles(self) -> List[Dict[str, Any]]:
        roles = getattr(self.project, "contributor_roles", {}) or {}
        selected_users = list(getattr(self.project, "authors", []) or [])
        entries: List[Dict[str, Any]] = []

        if roles:
            role_users = selected_users if selected_users else list(roles.keys())
            for user in role_users:
                info = roles.get(user)
                if not info:
                    continue
                role_key = info.get("primary_role", "role_none")
                role_name = self._pretty_role(role_key)
                confidence = float(info.get("confidence", 0.0) or 0.0)
                entries.append({
                    "name": user,
                    "role": role_name if role_name != "None" else "Contributor",
                    "confidence": confidence,
                    "confidence_pct": int(round(confidence * 100)),
                })

        if not entries and selected_users:
            for user in selected_users:
                entries.append({
                    "name": user,
                    "role": "Contributor",
                    "confidence": 0.0,
                    "confidence_pct": 0,
                })

        entries.sort(key=lambda item: item["name"].lower())
        return entries

    def _select_project_role(self, team_count: int, contributor_roles: List[Dict[str, Any]]) -> str:
        if contributor_roles:
            primary_role = contributor_roles[0].get("role", "")
            if primary_role and primary_role != "Contributor":
                if team_count > 1:
                    return f"{primary_role} Contributor (Team of {team_count})"
                return f"{primary_role} Developer"

        if team_count > 1:
            return f"Team Contributor (Team of {team_count})"
        return "Solo Developer"
