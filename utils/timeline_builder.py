from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Iterable, Dict, List, Tuple, Optional


def _to_date(value: Any) -> date:
    """
    Normalize various date-like inputs to datetime.date.

    Accepts:
      - datetime.date (but not datetime.datetime subclass)
      - datetime.datetime (converted via .date())
      - ISO-8601 date string "YYYY-MM-DD"

    Returns:
      datetime.date

    Raises:
      ValueError if the value cannot be interpreted as a date.
    """
    # Already a date (but not a datetime)
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    # datetime -> use .date()
    if isinstance(value, datetime):
        return value.date()

    # Try ISO-8601 string
    if isinstance(value, str):
        # Allow "YYYY-MM-DD" or things datetime.fromisoformat understands
        try:
            dt = datetime.fromisoformat(value)
            return dt.date()
        except ValueError:
            # Try a plain date parse as a fallback
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass

    raise ValueError(f"Unsupported or missing date value: {value!r}")


def _normalized_project_skills(skills: Iterable[str] | None) -> List[str]:
    """
    Take a list of skills and return a cleaned, deduplicated, case-insensitive
    sorted list while preserving the casing of the first occurrence.

    - Non-string items are ignored.
    - Empty or whitespace-only strings are ignored.
    - Deduplication is case-insensitive.
    - Sorting is case-insensitive, but final output preserves original casing
      from the first occurrence for each skill.
    """
    seen: Dict[str, str] = {}

    for s in skills or []:
        if not isinstance(s, str):
            continue
        t = s.strip()
        if not t:
            continue
        key = t.lower()
        # First appearance wins for casing
        if key not in seen:
            seen[key] = t

    # Sort by the lowercased key, but keep the original casing in the result
    return [seen[k] for k in sorted(seen.keys())]


@dataclass(order=True)
class SkillEvent:
    """
    A single skill usage event in time.
    """
    when: date
    skill: str
    project: Optional[str] = None


def build_timeline(projects: Iterable[Dict[str, Any]] | None) -> List[SkillEvent]:
    """
    Build a chronological list of skill usage events from a list of project dicts.

    Each project item may contain one of: "date", "start_date", or "end_date".
    Priority: date > start_date > end_date.

    Expected project structure (loosely):
      {
        "name": "Project Name",
        "skills": ["python", "pytest", ...],
        "date": "YYYY-MM-DD" | datetime | date,
        # or
        "start_date": ...,
        "end_date": ...,
      }

    Returns:
      List[SkillEvent] sorted by (when, skill, project).
    """
    events: List[SkillEvent] = []

    for p in projects or []:
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)
        name = p.get("name")
        for s in _normalized_project_skills(p.get("skills")):
            events.append(SkillEvent(when=when, skill=s, project=name))

    # SkillEvent is order=True so this sorts by (when, skill, project)
    events.sort()
    return events


def first_use_by_skill(projects: Iterable[Dict[str, Any]] | None) -> List[Tuple[str, date]]:
    """
    Return a list of (skill, first_seen_date) pairs, derived from the given
    project list.

    - Internally uses build_timeline(projects).
    - If a skill appears multiple times across projects, only the earliest date
      is retained.
    - Result is ordered by (first_seen_date, skill name case-insensitively).
    - For empty input, returns [].
    """
    first_seen: Dict[str, date] = {}

    for ev in build_timeline(projects):
        if ev.skill not in first_seen:
            first_seen[ev.skill] = ev.when

    # Sorted by date then by skill name (case-insensitive)
    return sorted(first_seen.items(), key=lambda kv: (kv[1], kv[0].lower()))


def projects_chronologically(projects: Iterable[Dict[str, Any]] | None) -> List[Tuple[date, str]]:
    """
    Return a list of (date, project_name) pairs sorted by date.

    - Uses the same date resolution as build_timeline: date > start_date > end_date.
    - Deduplicates by project name (first occurrence wins).
    - Raises ValueError if a project's date is missing/invalid.
    """
    seen_names = set()
    ordered: List[Tuple[date, str]] = []

    for p in projects or []:
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)
        name = p.get("name")
        if not name or name in seen_names:
            continue
        ordered.append((when, name))
        seen_names.add(name)

    ordered.sort(key=lambda x: x[0])
    return ordered


def projects_with_skills_chronologically(
    projects: Iterable[Dict[str, Any]] | None
) -> List[Tuple[date, str, List[str]]]:
    """
    Return a list of (date, project_name, [skills...]) sorted by date.

    - Date resolution: date > start_date > end_date.
    - Each project appears once (deduped by name).
    - Skills are unique per project and sorted case-insensitively,
      with casing preserved from the first occurrence.
    - Raises ValueError if a project's date is missing/invalid.
    """
    seen_names = set()
    rows: List[Tuple[date, str, List[str]]] = []

    for p in projects or []:
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)
        name = p.get("name")
        if not name or name in seen_names:
            continue

        skills = _normalized_project_skills(p.get("skills"))
        rows.append((when, name, skills))
        seen_names.add(name)

    rows.sort(key=lambda r: r[0])
    return rows


__all__ = [
    "_to_date",
    "_normalized_project_skills",
    "SkillEvent",
    "build_timeline",
    "first_use_by_skill",
    "projects_chronologically",
    "projects_with_skills_chronologically",
]
