# src/services/InsightEditor.py
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PortfolioParts:
    title: str
    role_line: str
    tech_line: str
    overview: str
    achievements: List[str]


class InsightEditor:
    @staticmethod
    def parse_portfolio_entry(text: str) -> PortfolioParts:
        lines = text.strip().splitlines()

        title = lines[0].strip() if lines else "### Project"
        role_line = ""
        tech_line = ""
        overview = ""
        achievements: List[str] = []

        # Find role + tech lines
        for i, ln in enumerate(lines[:6]):
            if ln.startswith("**Role:**"):
                role_line = ln.strip()
            if ln.startswith("**Technologies:**"):
                tech_line = ln.strip()

        # Overview block
        m_overview = re.search(r"\*\*Project Overview:\*\*\n(.+?)(?:\n\n|\n\*\*|$)", text, flags=re.S)
        if m_overview:
            overview = m_overview.group(1).strip()

        # Achievements bullets
        m_ach = re.search(r"\*\*Key Technical Achievements:\*\*\n(.+)$", text, flags=re.S)
        if m_ach:
            ach_block = m_ach.group(1).strip()
            achievements = []
            for ln in ach_block.splitlines():
                ln = ln.strip()
                if ln.startswith("* "):
                    achievements.append(ln[2:].strip())

        return PortfolioParts(
            title=title,
            role_line=role_line,
            tech_line=tech_line,
            overview=overview,
            achievements=achievements,
        )

    @staticmethod
    def build_portfolio_entry(parts: PortfolioParts) -> str:
        entry = []
        entry.append(parts.title)
        if parts.role_line:
            entry.append(parts.role_line)
        if parts.tech_line:
            entry.append(parts.tech_line)
        entry.append("")
        entry.append("**Project Overview:**")
        entry.append(parts.overview if parts.overview else "(no overview)")
        entry.append("")
        entry.append("**Key Technical Achievements:**")
        if parts.achievements:
            for a in parts.achievements:
                entry.append(f"* {a}")
        else:
            entry.append("* Delivered a functional codebase using modern development practices.")
        return "\n".join(entry) + "\n"
