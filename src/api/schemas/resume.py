from pydantic import BaseModel

class TodoResponse(BaseModel):
    ok: bool = False
    message: str