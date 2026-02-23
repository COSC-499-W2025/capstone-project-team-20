from pydantic import BaseModel
from typing import List, Optional


class BadgeProjectRef(BaseModel):
    id: Optional[int] = None
    name: str


class BadgeProgressItem(BaseModel):
    badge_id: str
    label: str
    metric: str
    target: float
    current: float
    progress: float
    project: BadgeProjectRef
    earned: bool


class BadgeProgressResponse(BaseModel):
    ok: bool = True
    badges: List[BadgeProgressItem]


class WrappedMilestone(BaseModel):
    badge_id: str
    project: str
    achieved_on: Optional[str] = None


class WrappedYear(BaseModel):
    year: int
    projects_count: int
    total_loc: int
    total_files: int
    avg_test_file_ratio: float
    milestones: List[WrappedMilestone]
    vibe_title: str
    highlights: List[str]


class YearlyWrappedResponse(BaseModel):
    ok: bool = True
    wrapped: List[WrappedYear]