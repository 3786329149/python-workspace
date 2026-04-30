from pydantic import BaseModel, Field
from uuid import UUID

class BindPasswordCommand(BaseModel):
    user_id: UUID
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterCommand(BaseModel):
    email: str
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
