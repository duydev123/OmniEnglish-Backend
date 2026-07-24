from datetime import datetime, timezone

from beanie import Document
from pydantic import EmailStr, Field


class UserModel(Document):
  username: str = Field(..., min_length=3, max_length=50)
  email: EmailStr
  password: str = Field(...)
  role: str = Field(default="user")
  createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  avartar: str
  class Settings:
    name = "users"