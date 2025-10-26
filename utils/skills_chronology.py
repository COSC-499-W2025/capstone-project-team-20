from dataclasses import dataclass
from datetime import datetime, date
from typing import Iterable, Dict, List, Tuple, Optional


def _to_date(value) -> date:
    """
    Returns: datetime.date
    Raises: ValueError on unsupported formats / None.
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


@dataclass(frozen=True, order=True)
class SkillEvent:
    when: date
    skill: str
    project: Optional[str] = None


def build_timeline(projects: Iterable[Dict]) -> List[SkillEvent]:
    """
    Project Item Shape:
    {
      "name": "Project A",
      "skills": ["python", "pytest"],
      "date": "2024-02-10"   # or "start_date" / "end_date" / datetime/date
    }
    Only one of date/start_date/end_date is required.
    """
    events: List[SkillEvent] = []
    for p in projects or []:
        # choose canonical date (date > start_date > end_date)
        when_raw = p.get("date") or p.get("start_date") or p.get("end_date")
        when = _to_date(when_raw)
        name = p.get("name")
        for s in p.get("skills") or []:
            if isinstance(s, str) and s.strip():
                events.append(SkillEvent(when=when, skill=s.strip(), project=name))
    events.sort()  # dataclass(order=True) -> (when, skill, project)
    return events


def first_use_by_skill(projects: Iterable[Dict]) -> List[Tuple[str, date]]:
    """
    Return [(skill, first_seen_date)] sorted by first_seen_date then skill name.
    """
    first_seen: Dict[str, date] = {}
    for ev in build_timeline(projects):
        if ev.skill not in first_seen:
            first_seen[ev.skill] = ev.when
    return sorted(first_seen.items(), key=lambda kv: (kv[1], kv[0].lower()))
