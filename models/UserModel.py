



import datetime

from beanie import Document
from pydantic import EmailStr, Field


class UserModel(Document):
  username: str = Field(..., min_length=3, max_length=50)
  email: EmailStr
  role: str = Field(default="user")
  createdAt: datetime = Field(default_factory=datetime.UTC)
  avarta: str
  class Settings:
    name = "users"