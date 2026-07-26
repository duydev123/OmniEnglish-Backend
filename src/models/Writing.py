from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import Document
from pydantic import Field


# ==========================================
# 1. BẢNG DỮ LIỆU ĐỀ THI WRITING (Gốc do Admin/System tạo)
# ==========================================
class WritingPromptModel(Document):
    title: str = Field(..., min_length=3)                      # VD: "Urban Dynamics" hoặc "Impact of AI..."
    task_type: str = Field(default="TASK_2")                  # "TASK_1" hoặc "TASK_2"
    task_description: str = Field(..., min_length=10)         # Đề bài mô tả chi tiết
    
    reference_image_url: Optional[str] = None                 # Ảnh tham chiếu (nếu là Task 1 hoặc đề bài ảnh)
    ref_id: Optional[str] = None                              # VD: "ARCH-204-URB"
    
    time_limit_minutes: int = Field(default=40)               # Thời gian làm bài (phút)
    word_count_target: int = Field(default=250)               # Số từ mục tiêu (VD: 250 - 500)
    
    # Gợi ý từ AI cho Writing Assistant
    suggested_structure: List[Dict[str, str]] = Field(default=[]) # [{"section": "Introduction", "guide": "..."}]
    advanced_vocabulary: List[str] = Field(default=[])            # ["Juxtaposition", "Obsolescence", ...]

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "writing_prompts"


# ==========================================
# 2. BẢNG LƯU BÀI LÀM & BÁO CÁO CHẤM AI (Full Essay & Review)
# ==========================================
class UserWritingSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    prompt_id: Optional[str] = None                           # ID bài thi gốc từ writing_prompts
    
    topic_title: str = Field(..., min_length=1)               # VD: "The Impact of Artificial Intelligence..."
    essay_content: str = Field(..., min_length=1)              # Nội dung bài viết gốc của User
    
    word_count: int = Field(default=0)                        # Số từ user đã viết
    time_spent_seconds: int = Field(default=0)                # Thời gian đã làm bài
    
    # --- ĐIỂM SỐ TỔNG & THỐNG KÊ TIÊU CHÍ (Góc trên & Góc dưới phải) ---
    overall_score: int = Field(default=0, ge=0, le=100)       # 75 Score
    general_summary: Optional[str] = None                     # "Your essay shows good structure..."
    
    # IELTS Band criteria (Area Performance)
    task_achievement_score: float = Field(default=0.0, ge=0, le=9.0) # 8.5/9.0
    lexical_resource_score: float = Field(default=0.0, ge=0, le=9.0)  # 7.5/9.0
    grammar_accuracy_score: float = Field(default=0.0, ge=0, le=9.0)  # 6.5/9.0
    coherence_cohesion_score: float = Field(default=0.0, ge=0, le=9.0)# 7.0/9.0

    # --- NHÃN HIGHLIGHT TRONG BÀI VIẾT (Dùng render màu chữ bên bài essay) ---
    # Example item: {"text": "improve", "type": "GRAMMAR", "feedback_index": 0}
    # Type: "GRAMMAR" (Đỏ), "WORD_CHOICE" (Vàng), "ADVANCED_LEXIS" (Xanh lá)
    highlight_spans: List[Dict] = Field(default=[])

    # --- CHI TIẾT GÓP Ý FEEDBACK (Cột Detailed Feedback) ---
    # Example item: {
    #    "type": "GRAMMAR",
    #    "original": "technology improve",
    #    "correction": "technology improves",
    #    "explanation": "Subject-verb agreement error..."
    # }
    detailed_feedbacks: List[Dict] = Field(default=[])

    status: str = Field(default="DRAFT")                      # "DRAFT" -> "SUBMITTED" -> "REVIEWED"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    potential_score: Optional[int] = Field(default=None) # Điểm tiềm năng (VD: 88)
    
    # Danh sách cặp so sánh (Original vs Improved)
    improvements_comparison: List[Dict] = Field(
        default=[],
        description="[{'category': 'Grammar', 'original': 'technology improve', 'improved': 'technology improves'}]"
    )

    # Lịch sử các cột mốc đã đạt được (Milestones)
    achieved_milestones: List[Dict[str, str]] = Field(
        default=[],
        description="[{'date': 'Oct 15', 'title': 'Achieved C1 Vocabulary'}]"
    )

    class Settings:
        name = "user_writing_sessions"
        indexes = [
            [("user_id", 1), ("created_at", -1)]
        ]