from datetime import date
from typing import Any, Dict, Iterable, List, Tuple, Optional

from git import Repo

from src.models.Project import Project
from utils.timeline_builder import (
    SkillEvent,
    build_timeline,
    projects_with_skills_chronologically,
)


def _skills_for_timeline(project: Project) -> List[str]:
    """
    Decide which skills to show in the timeline for a given project.

    For now, we only use languages, which are the most reliable signal.
    Later, we can add frameworks/other skills once their detection is
    more stable.
    """
    skills: List[str] = []

    # Only use languages for the timeline to avoid noisy tools/frameworks.
    if project.languages:
        skills.extend(project.languages)

    # Deduplicate while preserving order (case-insensitive compare, but keep
    # original casing for display).
    seen = set()
    deduped: List[str] = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return deduped


def _commit_date_for_timeline(project: Project) -> Optional[date]:
    """
    Try to derive a commit-based date for the project, using the earliest
    commit in its Git history.

    IMPORTANT:
      - This is ONLY used for the skill chronology functions in this module.
      - We do NOT write these dates back into the Project object, so other
        parts of the system (DB, reports, etc.) continue to behave as before.
    """
    repo_path = getattr(project, "file_path", None)
    if not repo_path:
        return None

    try:
        repo = Repo(str(repo_path))
    except Exception:
        # Not a git repo or not accessible → fall back to existing project dates.
        return None

    first: Optional[date] = None

    try:
        for commit in repo.iter_commits():
            dt = commit.committed_datetime
            if dt is None:
                continue
            d = dt.date()
            if first is None or d < first:
                first = d
    except Exception:
        # Any issue walking history → just fall back to existing project dates.
        return None

    return first


def _project_to_timeline_dict(project: Project) -> Optional[Dict[str, Any]]:
    """
    Convert a Project instance into the lightweight dict format expected
    by utils.timeline_builder.

    For chronology, we prefer Git commit dates:

      1. Earliest commit date in the repo (if available).
      2. Otherwise, fall back to the original project timestamps:
         - date_created
         - last_modified
         - last_accessed

    This logic is **only** used by the timeline/skill chronology features.
    """
    # 1) Try to use commit-based date (ONLY for this timeline view).
    when: Optional[date] = _commit_date_for_timeline(project)

    # 2) Fallback to previously existing behavior if no commit info.
    if when is None:
        when = (
            project.date_created
            or project.last_modified
            or project.last_accessed
        )

    if when is None:
        # If we still can't find a date, skip this project in the timeline.
        return None

    skills = _skills_for_timeline(project)
    if not skills:
        return None

    return {
        "name": project.name,
        "date": when,
        "skills": skills,
    }


def get_skill_timeline_from_projects(projects: Iterable[Project]) -> List[SkillEvent]:
    """
    Build a chronological list of SkillEvent objects (when, skill, project_name)
    for the given projects.

    The dates come from `_project_to_timeline_dict`, which now uses commit dates
    when available, but does NOT mutate the Project objects themselves.
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
    or JSON export. The dates are commit-based when Git history is available,
    but this logic is isolated to this module.
    """
    project_dicts: List[Dict[str, Any]] = []

    for proj in projects:
        row = _project_to_timeline_dict(proj)
        if row is not None:
            project_dicts.append(row)

    return projects_with_skills_chronologically(project_dicts)
