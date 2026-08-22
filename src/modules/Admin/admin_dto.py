from pydantic import BaseModel, Field
from typing import Optional

class ContentSetDTO(BaseModel):
    id: str
    category: str
    badge: str
    title: str
    itemsCount: int
    itemUnit: str = "Words"
    status: str = "Published"
    updatedAt: str
    type: str = "vocab"

class CreateContentSetRequest(BaseModel):
    title: str = Field(..., min_length=2)
    category: str = Field(default="GENERAL")
    itemsCount: int = Field(default=20)
    status: str = Field(default="Published")
    type: str = Field(default="vocab")

class UpdateContentSetRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    badge: Optional[str] = None
    itemsCount: Optional[int] = None
    status: Optional[str] = None

class AdminCMSStatsDTO(BaseModel):
    totalVocabItems: int
    publishedSets: int
    draftsPending: int

class AdminUserDTO(BaseModel):
    id: str
    username: str
    email: str
    role: str = "Student" # Student or Admin
    avatar: str = ""
    proficiency_level: str = "B2" # e.g. B2, C2, A1
    proficiency_label: str = "Upper Int." # e.g. Upper Int., Mastery, Beginner
    status: str = "Active" # Active or Suspended
    joined_date: str

class CreateAdminUserRequest(BaseModel):
    username: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    password: Optional[str] = "123456"
    role: str = Field(default="Student")
    proficiency_level: str = Field(default="B2")
    status: str = Field(default="Active")

class UpdateAdminUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    proficiency_level: Optional[str] = None
    status: Optional[str] = None

