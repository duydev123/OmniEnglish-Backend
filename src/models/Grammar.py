from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import Document, Link
from pydantic import Field


# ==========================================
# 1. BẢNG CHỦ ĐỀ NGỮ PHÁP & LÝ THUYẾT (Grammar Lesson & Guide)
# ==========================================
class GrammarTopicModel(Document):
    title: str = Field(..., min_length=3)                     # VD: "Error Identification" hoặc "Advanced Lexical Forms"
    level: str = Field(default="Intermediate B2")             
    
    # Cột lý thuyết Grammar Guide / Mẹo bên phải UI
    rule_title: Optional[str] = None                          
    rule_description: Optional[str] = None                   
    formula: Optional[str] = None                             
    quick_reference: List[Dict[str, str]] = Field(default=[]) 

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "grammar_topics"


# ==========================================
# 2. BẢNG CÂU HỎI BÀI TẬP NGỮ PHÁP (Phủ cả 4 dạng bài)
# ==========================================
class GrammarQuestionModel(Document):
    topic_id: Link[GrammarTopicModel]
    
    # Loại câu hỏi: 
    # - MULTIPLE_CHOICE (Trắc nghiệm)
    # - FILL_IN_BLANK (Điền từ)
    # - ERROR_IDENTIFICATION (Tìm lỗi sai A, B, C, D)
    # - WORD_FORM (Biến đổi dạng từ)
    question_type: str = Field(
        ..., 
        pattern="^(MULTIPLE_CHOICE|FILL_IN_BLANK|ERROR_IDENTIFICATION|WORD_FORM)$"
    )
    
    question_text: str = Field(..., min_length=1)             # Đoạn văn bản chứa câu hỏi
    context_image_url: Optional[str] = None                  # Ảnh minh họa Scenario Focus / Context
    scenario_focus_title: Optional[str] = None                # VD: "Corporate Achievement"
    
    # Dành cho ERROR_IDENTIFICATION:
    # Mảng 4 phần gạch chân: [{"key": "A", "text": "the fact that"}, {"key": "B", "text": "five years,"}, ...]
    underlined_options: List[Dict[str, str]] = Field(default=[]) 
    
    # Dành cho WORD_FORM:
    base_word: Optional[str] = None                           # VD: "SUCCESS"
    
    # Đáp án đúng
    correct_answer: str = Field(..., min_length=1)           # VD: "C" (cho Error ID) hoặc "success" (cho Word Form)
    
    # Các Box hỗ trợ trên UI
    grammar_tip: Optional[str] = None                         # Box "Did you know?" hoặc "Learning Tips"
    hint_text: Optional[str] = None                           # Text cho nút "Get a Hint"
    recommended_path_title: Optional[str] = None              # Learning Path đề xuất (VD: "Gerunds vs Infinitives")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "grammar_questions"


# ==========================================
# 3. BẢNG LƯU BÀI LÀM NGỮ PHÁP CỦA USER
# ==========================================
class UserGrammarSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    topic_id: Link[GrammarTopicModel]
    
    completed_tasks: int = Field(default=0)                   # Task 4 of 12
    total_tasks: int = Field(default=12)
    
    practice_time_seconds: int = Field(default=0)             # Session Time (VD: 14:02 = 842s)
    accuracy_rate: float = Field(default=0.0)                 # Accuracy Rate 92%
    xp_earned: int = Field(default=0)                         
    
    user_answers: Dict = Field(default={})                    # Đáp án user chọn/điền
    score: int = Field(default=0)                              
    status: str = Field(default="IN_PROGRESS")                # "IN_PROGRESS" -> "COMPLETED"
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_grammar_sessions"
        indexes = [
            [("user_id", 1), ("topic_id", 1)]
        ]