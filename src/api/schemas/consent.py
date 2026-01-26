"""API data model with pydantic. using BaseModel"""
from pydantic import BaseModel

class ConsentResponse(BaseModel):
    ok: bool = True
    consent: bool