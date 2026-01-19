from pydantic import BaseModel
from typing import Optional, List

class Portfolio(BaseModel):
    """Placeholder schema for (future) portfolio entity.
    does NOT represent a fully generated portfolio yet.
    will need to update once we have in place."""
    id: Optional[int] = None
    project_ids:List[int] = []
    title: Optional[str] = None
    description: Optional[str] = None

class PortfolioResponse(BaseModel):
    ok: bool = False
    portfolio: Optional[Portfolio] = None
    message: str