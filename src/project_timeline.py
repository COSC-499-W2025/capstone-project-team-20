from datetime import date
from typing import Any, Dict, Iterable, List, Tuple, Optional

from src.Project import Project
from utils.timeline_builder import (
    SkillEvent,
    build_timeline,
    projects_with_skills_chronologically,
)


def _project_to_timeline_dict(project: Project) -> Optional[Dict[str, Any]]:
    """
    Convert a Project instance into the lightweight dict format expected
    by utils.timeline_builder.

    Chooses a date in this priority order:
      - date_created
      - last_modified
      - last_accessed

    Returns None if no usable date is available.
    """
    when = project.date_created or project.last_modified or project.last_accessed
    if when is None:
        return None

    # Treat "skills" as the union of languages, frameworks, and skills_used.
    skills: List[str] = []
    for seq in (project.languages, project.frameworks, project.skills_used):
        if seq:
            skills.extend(seq)

    return {
        "name": project.name,
        "date": when,
        "skills": skills,
    }


def get_skill_timeline_from_projects(
    projects: Iterable[Project],
) -> List[SkillEvent]:
    """
    Return a chronological list of SkillEvent objects for the given projects.

    Each event represents a (date, project, skill) tuple, sorted by date.
    """
    project_dicts: List[Dict[str, Any]] = []

    for proj in projects:
        row = _project_to_timeline_dict(proj)
        if row is not None:
            project_dicts.append(row)

    return build_timeline(project_dicts)


def get_projects_with_skills_timeline_from_projects(
    projects: Iterable[Project],
) -> List[Tuple[date, str, List[str]]]:
    """
    Return a chronological list of (date, project_name, [skills...]) tuples
    for the given projects.

    This is a higher-level, project-centric view suitable for CLI output
    or JSON export.
    """
    project_dicts: List[Dict[str, Any]] = []

    for proj in projects:
        row = _project_to_timeline_dict(proj)
        if row is not None:
            project_dicts.append(row)

    return projects_with_skills_chronologically(project_dicts)
