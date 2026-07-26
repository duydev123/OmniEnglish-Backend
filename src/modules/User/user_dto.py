from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

# --- Request Đăng ký ---
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50) #
    email: EmailStr                                         #
    password: str = Field(..., min_length=6)

# --- Request Đăng nhập ---
class LoginRequest(BaseModel):
    email: EmailStr                                         #
    password: str

# --- Response Trả về Token ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str                                           #[cite: 17]
    role: str                                               #[cite: 17]






# --- Sub-Schema Cài đặt ---
class UserSettingsResponse(BaseModel):
    focus_areas: List[str]                                  #[cite: 17]
    daily_word_target: int                                  #[cite: 17]
    learning_mode: str                                      #[cite: 17]
    weekend_mastery: bool                                   #[cite: 17]
    base_language: str                                      #[cite: 17]
    notifications_enabled: bool                             #[cite: 17]

# --- Sub-Schema Thống kê chỉ số ---
class UserStatsResponse(BaseModel):
    current_streak_days: int                                #[cite: 17]
    total_xp: int                                           #[cite: 17]
    weekly_xp: int                                          #[cite: 17]
    total_words_learned: int                                #[cite: 17]
    total_speaking_hours: float                             #[cite: 17]
    general_english_level: str                              #[cite: 17]
    business_english_progress: float                        #[cite: 17]
    avg_reading_score: float                                #[cite: 17]
    avg_listening_score: float                              #[cite: 17]
    avg_speaking_score: float                               #[cite: 17]
    avg_writing_score: float                                #[cite: 17]

# --- Schema Tổng Profile Trả Về ---
class UserProfileResponse(BaseModel):
    id: str
    username: str                                           #[cite: 17]
    email: EmailStr                                         #[cite: 17]
    role: str                                               #[cite: 17]
    avatar: Optional[str] = None                            #[cite: 17]
    proficiency_level: str                                  #[cite: 17]
    status: str                                             #[cite: 17]
    
    settings: UserSettingsResponse                          #[cite: 17]
    stats: UserStatsResponse                                #[cite: 17]