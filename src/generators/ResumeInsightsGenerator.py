import random

class ResumeInsightsGenerator:
    """
    Generates resume bullet points and summaries, 
    """

    def __init__(self, metadata, categorized_files, language_share, project):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project

        # rotating words for variation in the bullet points/summaries
        self.verbs = [
            "Engineered",
            "Developed",
            "Implemented",
            "Designed",
            "Built",
            "Contributed to",
            "Refactored",
            "Enhanced"
        ]

        # Rotating impact phrases, mostly neutral and can be applied across basically all projects
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

    def get_category_counts(self):
        counts = self.categorized_files.get("counts", {})
        code_files = counts.get("code", 0)
        doc_files = counts.get("docs", 0)
        test_files = counts.get("test", 0) or counts.get("tests", 0)
        config_files = counts.get("config", 0)
        return code_files, doc_files, test_files, config_files

    def generate_resume_bullet_points(self) -> list[str]:
        # Resume bullet points
        bullets = []

        # Extract counts of all files
        code_files, doc_files, test_files, config_files = self.get_category_counts()

        # Project metadata
        authors = getattr(self.project, "authors", [])
        team_size = getattr(self.project, "author_count", len(authors))
        langs_sorted = list(self.language_share.keys())
        top_langs = ", ".join(langs_sorted[:3]) if langs_sorted else "multiple languages"

        verb = random.choice(self.verbs)
        impact = random.choice(self.impact_phrases)

        # ------- Bullet 1: Tech + Contribution -------
        bullets.append(
            f"{verb} core features using {top_langs}, contributing to a codebase of {code_files}+ well-structured source files."
        )

        # ------- Bullet 2: Docs + Tests -------
        if doc_files > 0 or test_files > 0:
            bullets.append(
                f"Produced {doc_files}+ documentation files and implemented {test_files} automated tests, {impact}."
            )

        # ------- Bullet 3: Duration -------
        duration = self._compute_project_duration()
        if duration:
            bullets.append(
                f"Iterated on the project across a {duration}-month development timeline, incorporating continuous updates and improvements."
            )

        # ------- Bullet 4: Collaboration vs Solo -------
        if team_size > 1:
            bullets.append(
                f"Collaborated with a team of {team_size} developers, leveraging Git-based workflows, code reviews, and coordinated issue tracking."
            )
        else:
            bullets.append(
                "Independently designed, implemented, and tested all major components of the system."
            )

        # ------- Bullet 5: Repo organization -------
        if config_files > 0:
            bullets.append(
                f"Structured the repository with {config_files} configuration files and an organized directory hierarchy to optimize project clarity and onboarding."
            )

        return bullets[:6]

    # ------------------------------------------------------------
    # Project Summary
    # ------------------------------------------------------------
    def generate_project_summary(self) -> str:

        code_files, doc_files, test_files, config_files = self.get_category_counts()
        counts = self.categorized_files["counts"]
        total_files = sum(counts.values())

        langs_sorted = list(self.language_share.keys())
        top_langs = ", ".join(langs_sorted[:4]) if langs_sorted else "multiple languages"

        duration = self._compute_project_duration()
        duration_text = f" over {duration} months" if duration else ""

        summary = (
            f"This software project was built using a tech stack of {top_langs}{duration_text}. "
            f"It follows a modular and maintainable architecture and contains over {total_files} files, including "
            f"{code_files} source modules, {test_files} automated tests, and "
            f"{doc_files} documentation files. "
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

    # ------------------------------------------------------------
    # Tech Stack
    # ------------------------------------------------------------
    def generate_tech_stack(self) -> str:
        langs_sorted = list(self.language_share.keys())
        if not langs_sorted:
            return "Tech Stack: Languages could not be detected"

        primary = ", ".join(langs_sorted[:6])
        return f"Tech Stack: {primary}"

    # ------------------------------------------------------------
    # Helper: Duration
    # ------------------------------------------------------------
    def _compute_project_duration(self):
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")
        if not start or not end:
            return None
        months = (end - start).days / 30.0
        return round(months, 1)
