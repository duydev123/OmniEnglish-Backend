from datetime import datetime, UTC
from typing import Optional, List
from beanie import Document
from pydantic import BaseModel, EmailStr, Field

class UserSettings(BaseModel):
    focus_areas: List[str] = Field(default_factory=lambda: ["General English"])
    daily_word_target: int = Field(default=30)
    learning_mode: str = Field(default="Steady Growth") 
    weekend_mastery: bool = Field(default=True)
    base_language: str = Field(default="vi-VN")
    notifications_enabled: bool = Field(default=True)


class UserStats(BaseModel):
    current_streak_days: int = Field(default=0)
    total_xp: int = Field(default=0)
    weekly_xp: int = Field(default=0)
    total_words_learned: int = Field(default=0)
    total_speaking_hours: float = Field(default=0.0)
    general_english_level: str = Field(default="B1")
    business_english_progress: float = Field(default=0.0)
    avg_reading_score: float = Field(default=0.0)
    avg_listening_score: float = Field(default=0.0)
    avg_speaking_score: float = Field(default=0.0)
    avg_writing_score: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserModel(Document):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    hashed_password: Optional[str] = None
    
    # Provider & Role
    auth_provider: str = Field(default="local")
    role: str = Field(default="user")                  # "user" hoặc "admin"
    avatar: Optional[str] = None
    
    # BỔ SUNG CHO ADMIN USER MANAGEMENT:
    proficiency_level: str = Field(default="B1")        # "A1", "A2", "B1", "B2", "C1", "C2"
    status: str = Field(default="Active")               # "Active", "Suspended", "Pending"
    
    # EMBEDDED SETTINGS & STATS
    settings: UserSettings = Field(default_factory=UserSettings)
    stats: UserStats = Field(default_factory=UserStats)

    # BỔ SUNG CHO ANALYTICS (DAU/MAU/Avg Session):
    last_login_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"
        indexes = [
            [("email", 1)],
            [("status", 1)],
            [("created_at", -1)]
        ]


class DailyActivityLogModel(Document):
    user_id: str = Field(..., min_length=1)
    date_str: str = Field(..., description="Định dạng YYYY-MM-DD")
    activities_count: int = Field(default=1) 
    xp_earned: int = Field(default=0)        
    
    class Settings:
        name = "daily_activity_logs"
   
        indexes = [[("user_id", 1), ("date_str", 1)]]