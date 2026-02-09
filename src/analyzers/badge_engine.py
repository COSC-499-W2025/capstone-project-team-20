# src/analyzers/badge_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set


@dataclass
class ProjectAnalyticsSnapshot:
    """
    Compact snapshot used to assign badges and generate fun facts.

    All fields are derived from existing analyzers:
      - metadata:     ProjectMetadataExtractor.compute_time_and_size_summary()
      - categories:   ProjectMetadataExtractor.compute_category_summary()
      - languages:    analyze_language_share()
      - skills:       SkillAnalyzer / FolderSkillAnalyzer
      - authors:      Git / ConfigManager usernames
    """
    name: str

    total_files: int
    total_size_kb: float
    total_size_mb: float
    duration_days: int

    category_summary: Dict[str, Dict[str, Any]]
    languages: Dict[str, float]      # language -> percentage share
    skills: Set[str]                 # e.g. {"Python", "React", "Docker"}

    author_count: int
    collaboration_status: str        # "individual" | "collaborative"

def _normalize_share(value: float) -> float:
    if value > 1.0:
        return value / 100.0
    return value

def _cat_metric(
    summary: Dict[str, Dict[str, Any]],
    category: str,
    keys: List[str],
    default: float = 0.0,
) -> float:
    """
    Safely pull a numeric metric from category_summary without hard-wiring its shape.

    It will try each key in `keys` until it finds a numeric value.
    """
    data = summary.get(category) or {}
    for k in keys:
        v = data.get(k)
        if isinstance(v, (int, float)):
            return _normalize_share(float(v))
    return default

def _category_share(summary: Dict[str, Dict[str, Any]], category: str, total_files: int) -> float:
    counts = summary.get("counts")
    if isinstance(counts, dict):
        count = counts.get(category, 0)
        if isinstance(count, (int, float)) and total_files > 0:
            return float(count) / float(total_files)
    return _cat_metric(summary, category, ["file_share", "files_pct", "share"], 0.0)


def assign_badges(snapshot: ProjectAnalyticsSnapshot) -> List[str]:
    """
    Core rules engine.

    Returns a list of stable badge IDs (strings). The frontend or CLI can map
    these IDs to human-readable labels, colors, and icons.
    """
    badges: List[str] = []

    size_mb = snapshot.total_size_mb
    files = snapshot.total_files
    duration = snapshot.duration_days
    langs = snapshot.languages or {}
    skills = snapshot.skills or set()
    cats = snapshot.category_summary or {}

    lang_count = len(langs)
    authors = snapshot.author_count

    # Category shares (backed by categories.yml)
    code_share = _category_share(cats, "code", files)
    test_share = _category_share(cats, "test", files)
    docs_share = _category_share(cats, "docs", files)
    design_share = _category_share(cats, "design", files)
    data_share = _category_share(cats, "data", files)
    game_share = _category_share(cats, "game", files)

    # ---------- Size / duration driven badges ----------

    if size_mb >= 1024:
        badges.append("gigantana")          # “Gigantanamamous”

    if duration >= 365:
        badges.append("slow_burn")

    if duration <= 7 and files >= 20:
        badges.append("flash_build")

    if duration <= 30 and files < 50:
        badges.append("fresh_breeze")

    if duration >= 730:
        badges.append("marathoner")

    if size_mb <= 5 and files >= 10:
        badges.append("tiny_but_mighty")

    if files >= 500 and duration <= 120:
        badges.append("rapid_builder")

    # ---------- Language diversity ----------

    lang_shares = [_normalize_share(v) for v in langs.values()]
    top_lang_share = max(lang_shares) if lang_shares else 0.0

    if lang_count >= 5:
        badges.append("jack_of_all_trades")
    elif lang_count >= 3:
        badges.append("polyglot")

    if top_lang_share >= 0.8:
        badges.append("language_specialist")

    if lang_count >= 3 and top_lang_share <= 0.5:
        badges.append("balanced_palette")

    # ---------- Collaboration profile ----------

    if authors <= 1:
        badges.append("solo_runner")
    elif authors >= 3:
        badges.append("team_effort")

    # ---------- Category-driven patterns (uses categories.yml) ----------

    if test_share >= 0.15:
        badges.append("test_pilot")

    if 0.05 <= test_share < 0.15:
        badges.append("test_scout")
    
    if docs_share >= 0.20:
        badges.append("docs_guardian")

    if 0.10 <= docs_share < 0.20:
        badges.append("doc_enthusiast")

    if design_share >= 0.25 or game_share >= 0.25:
        badges.append("pixel_perfect")

    if 0.15 <= max(design_share, game_share) < 0.25:
        badges.append("visual_storyteller")

    if 0.10 <= data_share < 0.25:
        badges.append("data_seedling")

    if data_share >= 0.25:
        badges.append("data_wrangler")

    if code_share >= 0.60:
        badges.append("code_cruncher")

    # ---------- Skill-driven badges (via SkillAnalyzer etc.) ----------

    if "Docker" in skills:
        badges.append("container_captain")

    if {"PyTest", "JUnit", "Jest", "Vitest"} & skills:
        if "test_pilot" not in badges:
            badges.append("test_pilot")

    if {"Pandas", "NumPy", "scikit-learn"} & skills:
        if "data_wrangler" not in badges:
            badges.append("data_wrangler")

    backend_langs = {"Python", "Java", "C#", "Go", "Rust", "PHP", "Ruby"}
    frontend_langs = {"JavaScript", "TypeScript"}
    has_backend = any(l in langs for l in backend_langs)
    has_frontend = any(l in langs for l in frontend_langs)
    has_react_stack = any(s in skills for s in {"React", "Next.js"})

    if has_backend and has_frontend and has_react_stack:
        badges.append("full_stack_explorer")

    return badges


def build_fun_facts(snapshot: ProjectAnalyticsSnapshot, badges: List[str]) -> List[str]:
    """
    Generate lightweight one-liner 'fun facts' for the analytics UI / CLI.
    """
    facts: List[str] = []

    if "gigantana" in badges:
        facts.append(
            f"{snapshot.name} weighs in at {snapshot.total_size_mb:.1f} MB of assets."
        )

    if snapshot.duration_days > 0:
        facts.append(
            f"{snapshot.name} has been evolving for {snapshot.duration_days} day(s)."
        )

    if "jack_of_all_trades" in badges or "polyglot" in badges:
        facts.append(
            f"{snapshot.name} speaks {len(snapshot.languages)} programming language(s)."
        )

    if "language_specialist" in badges and snapshot.languages:
        top_lang = max(snapshot.languages, key=snapshot.languages.get)
        facts.append(f"{snapshot.name} leans heavily on {top_lang} for core logic.")

    if "balanced_palette" in badges:
        facts.append("Language usage is well-balanced across the codebase.")

    if "solo_runner" in badges:
        facts.append("Built by a solo contributor from the ground up.")
    elif "team_effort" in badges:
        facts.append(
            f"Shaped by a team of {snapshot.author_count} collaborator(s)."
        )

    if "test_pilot" in badges:
        facts.append("Test code represents a meaningful slice of this codebase.")

    if "docs_guardian" in badges:
        facts.append("Rich documentation footprint detected across the repo.")

    if "doc_enthusiast" in badges:
        facts.append("Documentation has a consistent, noticeable presence.")

    if "pixel_perfect" in badges:
        facts.append("Design and media assets play a major role in this project.")

    if "visual_storyteller" in badges:
        facts.append("Visual assets provide a solid supporting role.")

    if "container_captain" in badges:
        facts.append("Containerization is part of this project’s deployment story.")

    if "marathoner" in badges:
        facts.append("This project has been evolving for multiple years.")

    if "tiny_but_mighty" in badges:
        facts.append("Compact in size, but packed with meaningful work.")

    if "rapid_builder" in badges:
        facts.append("A large amount of work landed in a tight timeframe.")

    if "test_scout" in badges:
        facts.append("Testing shows up regularly throughout the repo.")

    if "data_seedling" in badges:
        facts.append("Data assets and pipelines are part of the project mix.")

    return facts


def aggregate_badges(projects: Iterable[object]) -> Dict[str, int]:
    """
    Aggregate how many projects earned each badge.

    - badge_id -> number of projects that have this badge.

    Works with any object that has a `badges` attribute (list of strings).
    """
    totals: Dict[str, int] = {}

    for proj in projects:
        badge_list = getattr(proj, "badges", None) or []
        for b in badge_list:
            totals[b] = totals.get(b, 0) + 1

    return totals
