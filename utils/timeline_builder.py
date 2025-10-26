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
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported or missing date value: {value!r}")


def _normalized_project_skills(skills: Iterable[str] | None) -> List[str]:
    
    seen: Dict[str, str] = {}
    for s in skills or []:
        if not isinstance(s, str):
            continue
        t = s.strip()
        if not t:
            continue
        k = t.lower()
        if k not in seen:
            seen[k] = t
    # sort by lowercased key, but keep original casing from first appearance
    return [seen[k] for k in sorted(seen.keys())]


@dataclass(frozen=True, order=True)
class SkillEvent:
    when: date
    skill: str
    project: Optional[str] = None


def build_timeline(projects: Iterable[Dict[str, Any]] | None) -> List[SkillEvent]:
    """
    Build a chronological list of skill usage events.

    Each project item may contain one of: "date", "start_date", or "end_date".
    Priority: date > start_date > end_date.

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
    events.sort()  # dataclass(order=True) -> (when, skill, project)
    return events


def first_use_by_skill(projects: Iterable[Dict[str, Any]] | None) -> List[Tuple[str, date]]:
    """
    Return a list of (skill, first_seen_date) pairs,
    ordered by first_seen_date then skill name (case-insensitive).
    """
    first_seen: Dict[str, date] = {}
    for ev in build_timeline(projects):
        if ev.skill not in first_seen:
            first_seen[ev.skill] = ev.when
    return sorted(first_seen.items(), key=lambda kv: (kv[1], kv[0].lower()))


def projects_chronologically(projects: Iterable[Dict[str, Any]] | None) -> List[Tuple[date, str]]:
    """
    Return a list of (date, project_name) pairs sorted by date.

    - Uses the same date resolution as build_timeline: date > start_date > end_date.
    - Deduplicates by project name (first occurrence wins).
    - Raises ValueError if a project's date is missing/invalid.
    """
    seen = set()
    ordered: List[Tuple[date, str]] = []

    for p in projects or []:
        name = p.get("name")
        if not name or name in seen:
            continue
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)
        ordered.append((when, name))
        seen.add(name)

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
        name = p.get("name")
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
