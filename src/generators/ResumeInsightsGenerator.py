from analyzers.language_detector import analyze_language_share


"""
Generates insights, bullet points, summaries for building a resume!
Description is based on the extracted metadata, categorized files,
and git repo stats.
"""

class ResumeInsightsGenerator:
    def __init__(self, metadata, categorized_files, language_share, project):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project

    def generate_resume_bullet_points(self) -> list[str]:
        """Return 3-6 strong resume bullet points describing project"""

        bullets = []

        code_files = self.categorized_files.get("code", 0)
        doc_files = self.categorized_files.get("docs", 0)
        test_files = self.categorized_files.get("tests", 0)
        config_files = self.categorized_files.get("config", 0)

        authors = getattr(self.project, "authors", [])
        team_size = getattr(self.project, "author_count", len(authors))
        collab_status = getattr(self.project, "collaboration_status", "unknown")

        langs_sorted = list(self.language_share.keys())
        top_langs = ", ".join(langs_sorted[:2]) if langs_sorted else "multiple languages"

        duration = self._compute_project_duration()

        # --- Bullet 1: What the project is built with ---
        bullets.append(
            f"Developed a project using {top_langs}, including {code_files} source code files."
        )

        # --- Bullet 2: Testing & documentation ---
        if doc_files > 0 or test_files > 0:
            bullets.append(
                f"Created {doc_files} documentation files and {test_files} automated tests to improve clarity and reliability."
            )

        # --- Bullet 3: Duration (if available) ---
        if duration:
            bullets.append(
                f"Completed over a {duration}-month development period with consistent iteration."
            )

        # --- Bullet 4: Collaboration or solo ---
        if team_size > 1:
            bullets.append(
                f"Collaborated with a team of {team_size} developers using Git-based workflows."
            )
        else:
            bullets.append("Individually designed and implemented all project components.")

        # --- Bullet 5: Config + organization ---
        if config_files > 0:
            bullets.append(
                f"Organized the project with {config_files} configuration files and structured directories."
            )

        return bullets[:6]  # max 6 bullets

    # ----------------------------------------
    # 2. PROJECT SUMMARY
    # ----------------------------------------
    def generate_project_summary(self) -> str:
        langs_sorted = list(self.language_share.keys())
        top_langs = ", ".join(langs_sorted[:4]) if langs_sorted else "multiple languages"

        duration = self._compute_project_duration()
        duration_text = f" over {duration} months" if duration else ""

        total_files = sum(self.categorized_files.values())

        summary = (
            f"This project was built using {top_langs}{duration_text}. "
            f"It consists of {total_files} total files, including "
            f"{self.categorized_files.get('code', 0)} code modules, "
            f"{self.categorized_files.get('tests', 0)} tests, and "
            f"{self.categorized_files.get('docs', 0)} documentation files. "
        )

        team_size = getattr(self.project, "author_count", 1)
        if team_size > 1:
            summary += f"The project was developed collaboratively by a team of {team_size} contributors."
        else:
            summary += "The project was developed independently."

        return summary

    # ----------------------------------------
    # 3. TECH STACK LINE
    # ----------------------------------------
    def generate_tech_stack(self) -> str:
        langs_sorted = list(self.language_share.keys())
        if not langs_sorted:
            return "Tech Stack: Languages not detected"

        primary = ", ".join(langs_sorted[:5])
        return f"Tech Stack: {primary}"

    # ----------------------------------------
    # Helper: Compute project duration
    # ----------------------------------------
    def _compute_project_duration(self):
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")

        if not start or not end:
            return None

        months = (end - start).days / 30.0
        return round(months, 1)