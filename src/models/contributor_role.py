from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Set, List
from enum import Enum


class RoleID(str, Enum):
    TECH_LEAD = "role_tech_lead"
    BACKEND = "role_backend"
    FRONTEND = "role_frontend"
    FULLSTACK = "role_fullstack"
    QA = "role_qa"
    DEVOPS = "role_devops"
    DOCS = "role_docs"
    NONE = "role_none"


@dataclass(frozen=True)
class ContributorSignals:
    """
    Input signals for role inference (per contributor).
    """
    username: str
    commit_share: float = 0.0  # 0..1

    # Per-user category breakdown (whatever shape you already compute)
    category_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Optional signals if you have them per user
    skills: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class RoleInference:
    """
    Output of the role inference engine.
    """
    primary_role: RoleID
    confidence: float  # 0..1
    secondary_roles: List[RoleID] = field(default_factory=list)

    # Useful for portfolio/debugging (e.g., {"docs":0.62,"test":0.11,"backend":0.20})
    evidence: Dict[str, float] = field(default_factory=dict)
