from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RegistrationProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    username: str | None = Field(default=None, min_length=3, max_length=64)
