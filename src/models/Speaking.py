from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import Document
from pydantic import Field


# ==========================================
# 1. BẢNG DỮ LIỆU ĐỀ THI SPEAKING (Gốc do Admin/System tạo)
# ==========================================
class SpeakingPromptModel(Document):
    part: str = Field(..., pattern="^(PART_1|PART_2|PART_3)$") 
    topic: str = Field(..., min_length=3)                     # VD: "Hometown & Studies"
    question_text: str = Field(..., min_length=3)             # VD: "Can you describe the town..."
    
    # Gợi ý trên UI
    useful_vocabulary: List[str] = Field(default=[])          
    ielts_tips: List[str] = Field(default=[])                 
    examiner_tip: Optional[str] = None                       
    response_structure: List[Dict[str, str]] = Field(default=[]) 

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "speaking_prompts"


# ==========================================
# 2. MODEL CHI TIẾT BÀI BÁO CÁO SPEAKING (FULL ANALYSIS)
# ==========================================
class UserSpeakingTestSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    prompt_id: Optional[str] = None
    
    test_type: str = Field(..., pattern="^(PART_1|PART_2|PART_3|SHADOWING)$") 
    title: str = Field(..., min_length=1)         # VD: "Speaking Part 1: Result Analysis"
    duration_str: Optional[str] = Field(default="00:00") # VD: "02:45"
    full_session_audio_url: Optional[str] = None # Audio tổng của cả lượt thi
    
    # --- ĐIỂM SỐ & SO SÁNH ---
    overall_band_score: float = Field(default=0.0, ge=0, le=9.0) # 7.5
    band_score_delta: float = Field(default=0.0)                 # +0.5 so với last attempt
    percentile_rank: Optional[str] = None                        # "Top 15% User"

    # 4 Tiêu chí
    pronunciation_score: float = Field(default=0.0, ge=0, le=10) # 8.0/10
    fluency_score: float = Field(default=0.0, ge=0, le=10)       # 7.2/10
    lexical_score: float = Field(default=0.0, ge=0, le=10)       # 7.5/10
    grammar_score: float = Field(default=0.0, ge=0, le=10)       # 7.0/10

    # --- ĐỂM MẠNH & CẦN CẢI THIỆN (Left Screen) ---
    # Key Strengths
    key_strengths: List[Dict[str, str]] = Field(
        default=[], 
        description="[{'title': 'Effective Collocations', 'desc': '...'}]"
    )
    
    # Areas for Growth (Lỗi cụ thể + Sửa lỗi)
    areas_for_growth: List[Dict] = Field(
        default=[],
        description="[{'category': 'PRONUNCIATION', 'title': 'Ending Sounds: /d/', 'desc': '...', 'tip': '...', 'incorrect': 'how to applied', 'correct': 'how to apply'}]"
    )

    # --- PHÂN TÍCH TỪNG CÂU HỎI (Questions Breakdown & Transcript) ---
    # Bao gồm: q_text, user_transcript (kèm highlight từ vựng/lỗi), audio_url
    questions_detail: List[Dict] = Field(default=[]) 

    # --- AI INSIGHTS & CHI TIẾT TIÊU CHÍ (Right Screen) ---
    ai_insights_summary: Optional[str] = None # "Bạn có xu hướng phát âm tốt..."
    detailed_criteria_feedback: List[Dict] = Field(
        default=[],
        description="List phân tích sâu từng mục Phát âm, Ngữ pháp, Độ lưu khoát"
    )

    # --- RECOMMENDATIONS & NEXT MILESTONES ---
    next_milestone: Optional[Dict] = Field(
        default=None, 
        description="{'title': 'Master Band 8.0 Fluency', 'tasks': ['...']}"
    )
    recommended_resources: List[Dict[str, str]] = Field(
        default=[],
        description="[{'title': '10 Cụm từ thông dụng...', 'type': 'VOCAB'}]"
    )
    
    status: str = Field(default="COMPLETED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_speaking_test_sessions"
        indexes = [
            [("user_id", 1), ("test_type", 1), ("created_at", -1)]
        ]