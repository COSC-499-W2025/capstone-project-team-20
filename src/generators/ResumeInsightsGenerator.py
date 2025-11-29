import random
from datetime import datetime
from typing import Tuple

class ResumeInsightsGenerator:
    """
    Generates resume bullet points and summaries.

    Called from the `generate_resume_insights()` method in ProjectAnalyzer

    Workflow from that method is:
        1. generate_resume_bullet_points()
        2. generator.generate_project_summary()
    """

    def __init__(self, metadata, categorized_files, language_share, project, language_list):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list

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
        counts = self.categorized_files.get("counts", {})
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
        total_files = sum(self.categorized_files["counts"].values())

        top_langs = ", ".join(self.language_list[:4]) if self.language_list else "multiple languages"

        days = self._compute_days()
        duration_text = f" {self.format_duration(days)}" if days > 0 else ""

        summary = (
            f"This software project was built using a tech stack of {top_langs} over {duration_text}. "
            f"It follows a modular and maintainable architecture and contains over {total_files} files, including "
            f"{code_files} source modules, {test_files} automated tests, and {doc_files} documentation files. "
        )

        team_size = getattr(self.project, "author_count", 1)
        if team_size > 1:
            summary += (
                f"Built collaboratively by a team of {team_size} contributors, the codebase "
                "follows Git-based workflows, iterative development, and shared ownership."
            )
        else:
            summary += (
                "Developed independently, the project demonstrates full-lifecycle ownership across design, "
                "implementation, testing, and documentation."
            )

        return summary


    def generate_tech_stack(self) -> str:
        langs_sorted = list(self.language_share.keys())
        if not langs_sorted:
            return "Tech Stack: Languages could not be detected"

        primary = ", ".join(langs_sorted[:6])
        return f"Tech Stack: {primary}"

    # Helper: Compute days
    def _compute_days(self) -> int:
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")

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
    def display_insights(bullets: list[str], summary:str) -> None:
        "Called from ProjectAnalyzer, iterates through each bullet point and prints them, and then prints the summary"
        print("Resume Bullet Points:")
        for b in bullets:
            print(f" • {b}")
        print("\nProject Summary:")
        print(summary)
        print("\n")

