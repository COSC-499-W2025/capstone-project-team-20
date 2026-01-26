import random
from datetime import datetime
from typing import Tuple, Dict, Any, List

from rich.console import Console
from rich.markdown import Markdown


class ResumeInsightsGenerator:
    """

    Generates resume bullet points and summaries using normalized
    category counts provided by FileCategorizer (VIA ProjectMetadataExtractor)

    This class does NOT categorize anything itself - all categorization
    is handled upstream by the YAML-driven FileCategorizer

    Called from the `generate_resume_insights()` method in ProjectAnalyzer

    Workflow from that method is:
        1. generate_resume_bullet_points()
        2. generator.generate_project_summary()
        3. generator.generate_portfolio_entry()

    """

    def __init__(self, metadata: Dict, categorized_files: Dict, language_share: Dict, project: Any, language_list: List[str]):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list
        self.console: Console = Console()


        # rotating words for variation in the bullet points/summaries
        self.verbs = [
            "Engineered",
            "Developed",
            "Implemented",
            "Designed",
            "Built",
            "Contributed to",
            "Enhanced"
        ]

        self.impact_phrases = [
            "improving project clarity",
            "enhancing maintainability",
            "supporting long-term scalability",
            "strengthening overall code organization",
            "improving project readability and structure",
            "helping future contributors onboard more easily",
            "supporting consistent development workflows",
            "ensuring a more reliable development process",
        ]

    # Category counts
    def get_category_counts(self) -> Tuple[int,int,int,int]:
        "Returns count of code, doc, test and config files"
        counts = self.categorized_files or {}

        code_files = counts.get("code", 0)
        doc_files = counts.get("docs", 0)
        test_files = counts.get("test", 0) or counts.get("tests", 0)
        config_files = counts.get("config", 0)
        return code_files, doc_files, test_files, config_files

    # Resume Bullet Points
    def generate_resume_bullet_points(self) -> list[str]:
        """Currently generates up to 5 bullet points,
        1. Contributions and language use
        2. Documentation and Testing (if applicable)
        3. Length of time spent on project
        4. Team-based collaboration (if applicable)
        5. Generation of config files (if applicable)
        """
        bullets = []

        code_files, doc_files, test_files, config_files = self.get_category_counts()
        authors = getattr(self.project, "authors", [])
        team_size = getattr(self.project, "author_count", len(authors))

        langs_sorted = sorted(self.language_share.items(), key=lambda x: x[1], reverse=True)
        top_langs = ", ".join([lang for lang, pct in langs_sorted[:4]]) if langs_sorted else "multiple languages"

        verb = random.choice(self.verbs)
        impact = random.choice(self.impact_phrases)

        # Bullet 1 — Tech + contribution
        bullets.append(
            f"{verb} core features using {top_langs}, contributing to a codebase of {code_files}+ well-structured source files."
        )

        # Bullet 2 — Docs + Tests
        if doc_files > 0 or test_files > 0:
            bullets.append(
                f"Produced {doc_files}+ documentation files and implemented {test_files} automated tests, {impact}."
            )

        # Bullet 3 — Duration in months/days
        days = self._compute_days()
        if days > 0:
            duration_text = self.format_duration(days)
            bullets.append(
                f"Iterated on the project across a {duration_text} development timeline, incorporating continuous updates and improvements."
            )

        # Bullet 4 — Collaboration vs Solo
        if team_size > 1:
            bullets.append(
                f"Collaborated with a team of {team_size} developers, leveraging Git-based workflows, code reviews, and coordinated issue tracking."
            )
        else:
            bullets.append(
                "Independently designed, implemented, and tested all major components of the system."
            )

        # Bullet 5 — Repo organization
        if config_files > 0:
            bullets.append(
                f"Structured the repository with {config_files} configuration files and an organized directory hierarchy to optimize project clarity and onboarding."
            )

        return bullets[:6]

    # Project Summary
    def generate_project_summary(self) -> str:
        """Generates a project summary (str) detailing tech stack, time spent,
        num files, code/doc/test file split, collaboration status (team-based or individual)
        """
        code_files, doc_files, test_files, config_files = self.get_category_counts()
        total_files = sum((self.categorized_files or {}).values())

        top_langs = ", ".join(self.language_list[:4]) if self.language_list else "multiple languages"

        days = self._compute_days()
        duration_text = f" over {self.format_duration(days)}" if days > 0 else ""

        summary = (
            f"This software project was built using a tech stack of {top_langs}{duration_text}. "
            f"It follows a modular and maintainable architecture and contains over {total_files} files, including "
            f"{code_files} source modules, {test_files} automated tests, and {doc_files} documentation files. "
        )

        team_size = getattr(self.project, "author_count", 1)
        if team_size > 1:
            summary += (
                f"Built collaboratively by a team of {team_size} developers, the codebase "
                "follows Git-based workflows, iterative development, and shared ownership."
            )
        else:
            summary += (
                "Developed independently, the project demonstrates full-lifecycle ownership across design, "
                "implementation, testing, and documentation."
            )

        return summary

    def generate_portfolio_entry(self) -> str:
        """
        Generates a structured portfolio entry following professional guidelines:
        - Clear role definition
        - Tech stack listing
        - Context/Overview
        - Key Technical Outcomes
        """
        code_files, _, _, _ = self.get_category_counts()
        total_files = sum((self.categorized_files or {}).values())

        # Duration
        days = self._compute_days()
        duration_str = self.format_duration(days)

        # Tech Stack
        langs = ", ".join(self.language_list[:4]) if self.language_list else "various technologies"

        # Role Logic — strictly use total author_count
        team_count = getattr(self.project, "author_count", 0)
        if team_count > 1:
            role = f"Team Contributor (Team of {team_count})"
            collaboration_text = f"collaborated with {team_count-1} other developers to build"
        else:
            role = "Solo Developer"
            collaboration_text = "independently designed and implemented"

        project_name = getattr(self.project, 'name', 'Project')

        # Overview
        overview = (
            f"A software solution {collaboration_text} over a {duration_str} period. "
            f"The codebase consists of {total_files} files, including {code_files} source modules, "
            f"structured for maintainability and scalability."
        )

        # Achievements
        achievements = []
        test_ratio = getattr(self.project, 'test_file_ratio', 0)
        if test_ratio > 0.15:
            achievements.append("Implemented a robust automated testing suite ensuring high code reliability.")
        elif test_ratio > 0:
            achievements.append("Integrated automated tests to support continuous integration.")
        doc_score = getattr(self.project, 'documentation_habits_score', 0)
        if doc_score > 75:
            achievements.append("Maintained comprehensive documentation to facilitate developer onboarding and maintenance.")
        loc = getattr(self.project, 'total_loc', 0)
        if loc > 5000:
            achievements.append(f"Architected a substantial codebase of over {loc:,} lines of code.")
        if not achievements:
            achievements.append("Delivered a functional codebase using modern development practices.")

        # Entry
        entry = f"### {project_name}\n"
        entry += f"**Role:** {role} | **Timeline:** {duration_str}\n"
        entry += f"**Technologies:** {langs}\n\n"
        entry += "**Project Overview:**\n"
        entry += f"{overview}\n\n"
        entry += "**Key Technical Achievements:**\n"
        for achievement in achievements:
            entry += f"* {achievement}\n"

        return entry

    def generate_tech_stack(self) -> str:
        if not self.language_share:
            return "Tech Stack: Languages could not be detected"

        primary = ", ".join(list(self.language_share.keys())[:6])
        return f"Tech Stack: {primary}"

    # Helper: Compute days
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

    # formatting for days if less than 1 month
    # or _ months and _ days if longer than 1 month
    def format_duration(self, days: int) -> str:
        if days < 30:
            return f"{days} days"

        months = days // 30
        remaining = days % 30

        if remaining == 0:
            return f"{months} month" + ("s" if months > 1 else "")

        return (
            f"{months} month" + ("s" if months > 1 else "")
            + f" and {remaining} days"
        )
    @staticmethod
    def display_insights(bullets: list[str], summary: str, portfolio_entry: str = "", console: Console = None) -> None:
        "Called from ProjectAnalyzer, iterates through each bullet point and prints them, and then prints the summary"
        console = console or Console()

        console.print("\n[bold]Resume Bullet Points:[/bold]")
        for b in bullets:
            console.print(f" • {b}")
        console.print("\n[bold]Project Summary:[/bold]")
        console.print(summary)

        if portfolio_entry:
            console.print("\n[bold]Portfolio Entry:[/bold]")
            console.print(Markdown(portfolio_entry))

        print("\n")
