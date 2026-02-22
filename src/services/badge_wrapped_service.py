from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from src.analyzers.badge_engine import ProjectAnalyticsSnapshot, assign_badges


BADGE_PROGRESS_RULES = {
    "test_pilot": {
        "label": "Test Pilot",
        "metric": "Test file ratio",
        "target": 0.15,
        "extractor": lambda p: _test_ratio(p),
    },
    "docs_guardian": {
        "label": "Docs Guardian",
        "metric": "Docs share",
        "target": 0.20,
        "extractor": lambda p: _category_ratio(p, "docs"),
    },
    "polyglot": {
        "label": "Polyglot",
        "metric": "Languages used",
        "target": 3.0,
        "extractor": lambda p: float(_language_count(p)),
    },
    "team_effort": {
        "label": "Team Effort",
        "metric": "Contributors",
        "target": 3.0,
        "extractor": lambda p: float(_author_count(p)),
    },
    "code_cruncher": {
        "label": "Code Cruncher",
        "metric": "Code share",
        "target": 0.60,
        "extractor": lambda p: _category_ratio(p, "code"),
    },
}

def _project_total_files(project) -> float:
    total = float(getattr(project, "num_files", 0) or 0)
    if total > 0:
        return total

    categories = getattr(project, "categories", {}) or {}
    counts = categories.get("counts") if isinstance(categories, dict) else None
    if isinstance(counts, dict):
        return float(sum(v for v in counts.values() if isinstance(v, (int, float))))

    if isinstance(categories, dict):
        return float(sum(v for v in categories.values() if isinstance(v, (int, float))))
    return 0.0

def _category_ratio(project, category: str) -> float:
    categories = getattr(project, "categories", {}) or {}
    count = 0.0

    if isinstance(categories, dict):
        counts = categories.get("counts")
        if isinstance(counts, dict):
            count = float(counts.get(category, 0) or 0)
        else:
            count = float(categories.get(category, 0) or 0)

    total = _project_total_files(project)

    if total <= 0:
        return 0.0
    return count / total


def _language_count(project) -> int:
    language_share = getattr(project, "language_share", {}) or {}
    if isinstance(language_share, dict) and len(language_share) > 0:
        return len(language_share)
    return len(getattr(project, "languages", []) or [])


def _author_count(project) -> int:
    count = int(getattr(project, "author_count", 0) or 0)
    if count > 0:
        return count
    return len(getattr(project, "authors", []) or [])


def _test_ratio(project) -> float:
    explicit_ratio = float(getattr(project, "test_file_ratio", 0.0) or 0.0)
    category_ratio = _category_ratio(project, "test")
    return max(explicit_ratio, category_ratio)


def _category_counts(project) -> dict:
    categories = getattr(project, "categories", {}) or {}
    if not isinstance(categories, dict):
        return {}
    counts = categories.get("counts")
    if isinstance(counts, dict):
        return counts
    return categories


def _project_badges(project) -> list[str]:
    duration_days = 0
    if getattr(project, "date_created", None) and getattr(project, "last_modified", None):
        duration_days = max((project.last_modified - project.date_created).days, 0)

    snapshot = ProjectAnalyticsSnapshot(
        name=project.name,
        total_files=getattr(project, "num_files", 0) or 0,
        total_size_kb=getattr(project, "size_kb", 0) or 0,
        total_size_mb=((getattr(project, "size_kb", 0) or 0) / 1024),
        duration_days=duration_days,
        category_summary={"counts": _category_counts(project)},
        languages=getattr(project, "language_share", {}) or {},
        skills=set(getattr(project, "skills_used", []) or []),
        author_count=_author_count(project),
        collaboration_status=getattr(project, "collaboration_status", "individual") or "individual",
    )
    return assign_badges(snapshot)


def _vibe_title(year: int, projects_count: int, total_loc: int, milestones_count: int) -> str:
    if milestones_count >= 8:
        return f"{year}: Trophy Collector 🏆"
    if total_loc >= 10000:
        return f"{year}: Code Symphony 🎼"
    if projects_count >= 5:
        return f"{year}: Builder Era 🚀"
    if milestones_count > 0:
        return f"{year}: Badge Breakthrough ✨"
    return f"{year}: Foundations Laid 🌱"


def _wrapped_highlights(projects_count: int, total_loc: int, total_files: int, milestones_count: int) -> list[str]:
    highlights = [
        f"Shipped {projects_count} project(s) this year.",
        f"Wrote {total_loc:,} total lines of code.",
        f"Touched {total_files:,} files across your repositories.",
    ]

    if milestones_count:
        highlights.append(f"Unlocked {milestones_count} badge milestone(s) this year.")
    else:
        highlights.append("No badge unlocks yet — next year is your glow-up arc.")

    if total_loc >= 5000:
        highlights.append("Long coding sessions paid off — this was a high-output year.")

    return highlights


def _project_year(project) -> int | None:
    stamp = getattr(project, "last_modified", None) or getattr(project, "date_created", None)
    if isinstance(stamp, datetime):
        return stamp.year
    return None


def build_badge_progress(projects) -> Dict[str, Any]:
    responses = []
    for badge_id, rule in BADGE_PROGRESS_RULES.items():
        closest_project = None
        closest_progress = -1.0
        current_value = 0.0

        for p in projects:
            metric_value = max(rule["extractor"](p), 0.0)
            progress = min(metric_value / rule["target"], 1.0) if rule["target"] > 0 else 0.0
            if progress > closest_progress:
                closest_progress = progress
                closest_project = p
                current_value = metric_value

        if closest_progress < 0:
            closest_progress = 0.0

        responses.append({
            "badge_id": badge_id,
            "label": rule["label"],
            "metric": rule["metric"],
            "target": rule["target"],
            "current": current_value,
            "progress": round(closest_progress, 3),
            "project": {
                "id": getattr(closest_project, "id", None),
                "name": getattr(closest_project, "name", "No project yet"),
            },
            "earned": closest_progress >= 1.0,
        })

    return {"ok": True, "badges": responses}


def build_yearly_wrapped(projects) -> Dict[str, Any]:
    yearly = {}
    for project in projects:
        year = _project_year(project)
        if year is None:
            continue

        bucket = yearly.setdefault(year, {
            "year": year,
            "projects_count": 0,
            "total_loc": 0,
            "total_files": 0,
            "avg_test_file_ratio": 0.0,
            "milestones": [],
            "vibe_title": "",
            "highlights": [],
        })

        bucket["projects_count"] += 1
        bucket["total_loc"] += int(getattr(project, "total_loc", 0) or 0)
        bucket["total_files"] += int(getattr(project, "num_files", 0) or 0)
        bucket["avg_test_file_ratio"] += float(getattr(project, "test_file_ratio", 0.0) or 0.0)

        earned_badges = _project_badges(project)
        for badge in earned_badges:
            bucket["milestones"].append({"badge_id": badge, "project": project.name})

    payload = []
    for year in sorted(yearly.keys(), reverse=True):
        item = yearly[year]
        if item["projects_count"] > 0:
            item["avg_test_file_ratio"] = round(item["avg_test_file_ratio"] / item["projects_count"], 3)

        milestones_count = len(item["milestones"])
        item["vibe_title"] = _vibe_title(year, item["projects_count"], item["total_loc"], milestones_count)
        item["highlights"] = _wrapped_highlights(item["projects_count"], item["total_loc"], item["total_files"], milestones_count)
        payload.append(item)

    return {"ok": True, "wrapped": payload}