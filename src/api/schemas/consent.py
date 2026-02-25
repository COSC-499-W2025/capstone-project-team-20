from pydantic import BaseModel

class ConsentRequest(BaseModel):
    consent: bool

class ConsentResponse(BaseModel):
    consent: bool