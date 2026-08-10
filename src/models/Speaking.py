from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

# ==========================================
# SUB-MODELS (Dùng để validate mảng dữ liệu trong document chính)
# ==========================================
class KeyStrengthItem(BaseModel):
    title: str
    desc: str

class AreaForGrowthItem(BaseModel):
    category: str
    title: str
    desc: str
    tip: str
    incorrect: str
    correct: str

class QuestionDetailItem(BaseModel):
    prompt_id: str
    question_text: str
    user_transcript: str
    user_audio_url: Optional[str] = None
    
    # Kết quả chấm NHANH (Realtime)
    pronunciation_score: Optional[float] = 0.0
    fluency_score: Optional[float] = 0.0
    overall_score: Optional[float] = 0.0 # Bỏ trường này đi, vì Overall Score của 1 câu không có ý nghĩa trong IELTS.
    segment_score: Optional[float] = 0.0 # Dùng điểm segment (vd: thang 10 hoặc 100) để đánh giá câu đó.
    lexical_score: Optional[float] = 0.0  # THÊM MỚI
    grammar_score: Optional[float] = 0.0  # THÊM MỚI
    ai_feedback: Optional[str] = None
    words_detail: List[dict] = Field(default=[])
    
    is_graded: bool = False # Đánh dấu đã chấm xong

class MilestoneItem(BaseModel):
    title: str
    tasks: List[str]

# ==========================================
# 1. BẢNG CHỦ ĐỀ / BỘ ĐỀ (Speaking Topic)
# ==========================================
class SpeakingTopicModel(Document):
    title: str = Field(..., min_length=3)                     # VD: "IELTS Speaking Mock Test 1" hoặc "Topic: Environment"
    description: Optional[str] = None                         # Mô tả ngắn gọn bộ đề
    tags: List[str] = Field(default=[])                       # VD: ["Environment", "Pollution"]
    is_full_test: bool = Field(default=False)                 # Đánh dấu True nếu bộ này gom đủ cả Part 1, 2, 3 để thi thật
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "speaking_topics"

# ==========================================
# 2. BẢNG CÂU HỎI LẺ (Speaking Prompt)
# ==========================================
class SpeakingPromptModel(Document):
    topic_id: Link[SpeakingTopicModel]                        # Bắt buộc link tới 1 chủ đề/bộ đề
    
    part: str = Field(..., pattern="^(PART_1|PART_2|PART_3|SHADOWING)$")
    sub_topic: Optional[str] = None                           # Dành cho Part 1 (VD: "Hometown", "Work", v.v.)
    
    question_text: str = Field(..., min_length=3)
    examiner_audio_url: Optional[str] = None                  # Giọng AI đọc câu hỏi
    
    # Gợi ý UI
    useful_vocabulary: List[str] = Field(default=[])
    ielts_tips: List[str] = Field(default=[])
    examiner_tip: Optional[str] = None
    response_structure: List[Dict[str, str]] = Field(default=[])
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "speaking_prompts"

# ==========================================
# 3. MODEL CHI TIẾT BÀI LÀM (User Session)
# ==========================================
class UserSpeakingTestSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    
    # User có thể luyện tập theo cả bộ đề hoặc luyện lẻ 1 câu
    topic_id: Optional[Link[SpeakingTopicModel]] = None       # Dành cho thi nguyên bộ đề (Full Test)
    prompt_id: Optional[Link[SpeakingPromptModel]] = None     # Dành cho luyện tập 1 câu lẻ
    
    test_type: str = Field(..., pattern="^(PART_1|PART_2|PART_3|SHADOWING|FULL_TEST)$")
    title: str = Field(..., min_length=1)
    duration_str: Optional[str] = Field(default="00:00")
    full_session_audio_url: Optional[str] = None
    
    # --- ĐIỂM & SO SÁNH ---
    overall_band_score: float = Field(default=0.0, ge=0, le=9.0)
    band_score_delta: float = Field(default=0.0)
    percentile_rank: Optional[str] = None
    
    # 4 Tiêu chí IELTS
    pronunciation_score: float = Field(default=0.0, ge=0, le=10)
    fluency_score: float = Field(default=0.0, ge=0, le=10)
    lexical_score: float = Field(default=0.0, ge=0, le=10)
    grammar_score: float = Field(default=0.0, ge=0, le=10)
    
    # --- NHẬN XÉT CHI TIẾT ---
    key_strengths: List[KeyStrengthItem] = Field(default=[]) 
    areas_for_growth: List[AreaForGrowthItem] = Field(default=[]) 
    questions_detail: List[QuestionDetailItem] = Field(default=[]) 
    
    # --- AI INSIGHTS & KẾ HOẠCH ---
    ai_insights_summary: Optional[str] = None
    detailed_criteria_feedback: List[Dict] = Field(default=[])
    
    next_milestone: Optional[MilestoneItem] = None
    recommended_resources: List[Dict[str, str]] = Field(default=[])
    
    status: str = Field(default="COMPLETED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_speaking_test_sessions"
        indexes = [
            [("user_id", 1), ("test_type", 1), ("created_at", -1)]
        ]