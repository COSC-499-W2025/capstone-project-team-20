from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Iterable, Dict, List, Tuple, Optional


def _to_date(value: Any) -> date:
    """
    Normalize various date-like inputs to datetime.date.

    Accepts:
      - datetime.date
      - datetime.datetime (converted via .date())
      - ISO-8601 date string "YYYY-MM-DD" (optionally with time)

    Raises:
      ValueError if the value is missing or cannot be interpreted as a date.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            # Allow full ISO-8601 strings (with time); we only keep the date part.
            return datetime.fromisoformat(value).date()
        except ValueError:
            raise ValueError(f"Unsupported date string: {value!r}") from None

    raise ValueError(f"Unsupported or missing date value: {value!r}")


@dataclass(frozen=True, order=True)
class SkillEvent:
    """
    Represents the use of a skill on a particular date in a project.

    Attributes
    ----------
    when:
        The calendar date on which the skill was exercised.
    skill:
        The skill / technology name (e.g., "Python", "React").
    project:
        Optional project name associated with the event.
    """
    when: date
    skill: str
    project: Optional[str] = None


def _normalized_project_skills(raw_skills: Any) -> List[str]:
    """
    Normalize a project's skills into a sorted, deduplicated list of strings.

    Behaviour:
    - Accepts None or any iterable of values.
    - Only string values are kept; non-strings (e.g. numbers) are ignored.
    - Strings are stripped; empty entries are ignored.
    - Skills are deduplicated *case-insensitively*, but casing from the first
      occurrence is preserved.
    - The returned list is sorted case-insensitively.
    """
    if not raw_skills:
        return []

    result: Dict[str, str] = {}  # lowercased -> original casing
    try:
        iterable = list(raw_skills)
    except TypeError:
        iterable = [raw_skills]

    for value in iterable:
        if value is None or not isinstance(value, str):
            continue
        s = value.strip()
        if not s:
            continue
        key = s.lower()
        if key not in result:
            result[key] = s

    return [result[k] for k in sorted(result.keys())]




def build_timeline(projects: Iterable[Dict[str, Any]]) -> List[SkillEvent]:
    """
    Build a chronological list of SkillEvent from project records.

    Each project dictionary may contain:
      - "name": project name (optional)
      - "date" or "start_date" or "end_date": a date-like value
      - "skills": iterable of skills / technologies used

    For every (project, skill) pair we emit a SkillEvent. Events are
    sorted by date, then by skill name, then by project name.
    """
    events: List[SkillEvent] = []

    for p in projects:
        # Determine project name (optional)
        project_name = p.get("name") or p.get("project") or None

        # Determine the date; this will raise ValueError if nothing valid is found.
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)

        skills = _normalized_project_skills(p.get("skills"))

        for skill in skills:
            events.append(SkillEvent(when=when, skill=skill, project=project_name))

    # dataclass(order=True) gives ordering by (when, skill, project)
    events.sort()
    return events


def first_use_by_skill(
    projects_or_events: Iterable[Any] | None,
) -> List[Tuple[str, date]]:
    """
    Return the first date on which each skill appears.

    Accepts either:
      - an iterable of project dicts (as expected by build_timeline), or
      - an iterable of SkillEvent objects.

    Returns:
      A list of (skill, date) tuples, where each skill appears once at its
      earliest date, sorted by (date, skill name, case-insensitive).

    This shape is compatible with tests that do both:
      - dict(firsts) == {skill: date, ...}
      - firsts == [(skill, date), ...] in a specific order.
    """
    items = list(projects_or_events or [])
    if not items:
        return []

    first = items[0]
    if isinstance(first, SkillEvent):
        events = items  # already SkillEvent objects
    else:
        # Treat input as project dicts and build SkillEvent list from them
        events = build_timeline(items)

    first_seen: Dict[str, date] = {}

    for ev in events:
        skill = ev.skill
        when = ev.when
        current = first_seen.get(skill)
        if current is None or when < current:
            first_seen[skill] = when

    # Convert mapping to a sorted list of (skill, date)
    rows: List[Tuple[str, date]] = [(skill, when) for skill, when in first_seen.items()]
    rows.sort(key=lambda sd: (sd[1], sd[0].lower()))  # (date, skill.lower())
    return rows


def projects_chronologically(
    projects: Iterable[Dict[str, Any]] | None,
) -> List[Tuple[date, str]]:
    """
    Return a list of (date, project_name) sorted by date.

    - Date resolution: date > start_date > end_date.
    - Each project appears at most once (deduplicated by name).
    - Raises ValueError if a project's date is missing/invalid.
    """
    seen_names = set()
    rows: List[Tuple[date, str]] = []

    for p in projects or []:
        name = p.get("name") or p.get("project")
        if not name or name in seen_names:
            continue

        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)

        rows.append((when, name))
        seen_names.add(name)

    rows.sort(key=lambda r: r[0])
    return rows


def projects_with_skills_chronologically(
    projects: Iterable[Dict[str, Any]] | None,
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
        name = p.get("name") or p.get("project")
        if not name or name in seen_names:
            continue

        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)

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
