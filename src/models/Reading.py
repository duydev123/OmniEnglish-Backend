from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import Document, Link
from pydantic import Field


# ==========================================
# 1. BẢNG BÀI ĐỌC READING (Passage & Đề thi gốc)
# ==========================================
class ReadingPassageModel(Document):
    topic: str = Field(..., min_length=3)
    title: str = Field(..., min_length=3)                     # VD: "The Rise of Digital Nomads"
    content: str = Field(..., min_length=10)                  # Nội dung bài đọc (HTML/Markdown)
    image_url: Optional[str] = None                         # URL ảnh minh họa trong bài đọc
    
    time_limit_minutes: int = Field(default=15)               # Thời gian làm bài (phút)
    total_questions: int = Field(default=20)                  # Tổng số câu hỏi trong bài đọc
    learning_tip: Optional[str] = None                        # Box "Learning Tip" góc dưới UI

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "reading_passages"


# ==========================================
# 2. CÁC DẠNG CÂU HỎI READING (Liên kết với Passage)
# ==========================================
class ReadingVocabMatchingModel(Document):
    passage_id: Link[ReadingPassageModel]                     # Link tới bài đọc
    order: int = Field(default=1)
    pairs: List[Dict[str, str]] = Field(..., min_items=1)     # [{"term": "Confluence", "definition": "..."}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "reading_vocab_matchings"


class ReadingSentenceCompletionModel(Document):
    passage_id: Link[ReadingPassageModel]          # Link tới bài đọc
    order: int = Field(default=2)
    template_text: str = Field(..., min_length=1)             # Đoạn văn chứa ô trống
    correct_answers: Dict[str, str] = Field(...)             # Đáp án đúng cho từng ô
    case_sensitive: bool = Field(default=False)               # Phân biệt hoa/thường
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "reading_sentence_completions"


class ReadingMultipleChoiceModel(Document):
    passage_id: Link[ReadingPassageModel]
    order: int = Field(default=3)
    question_text: str = Field(..., min_length=1)             # Câu hỏi trắc nghiệm
    options: List[str] = Field(..., min_items=2)              # Các lựa chọn
    correct_answer: str = Field(..., min_length=1)           # Đáp án đúng
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "reading_multiple_choices"


# ==========================================
# 3. BẢNG LƯU LƯỢT LÀM BÀI READING CỦA USER
# ==========================================
class UserReadingSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    passage_id: Link[ReadingPassageModel]
    attempt_number: int = Field(default= 1, ge=1)
    
    # Tiến độ & Thời gian
    completed_questions: int = Field(default=0)              # VD: 13
    total_questions: int = Field(default=20)                  # VD: 20
    time_remaining_seconds: int = Field(default=0)            # VD: 765s (12:45)
    
    # Đáp án User đã chọn/điền (dạng JSON lưu vết)
    user_answers: Dict = Field(default={})                    
    
    score: int = Field(default=0)                              # Số câu đúng
    status: str = Field(default="IN_PROGRESS")                # "IN_PROGRESS" -> "COMPLETED"
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    start_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    class Settings:
        name = "user_reading_sessions"
        indexes = [
            [("user_id", 1), ("passage_id", 1), ("attempt_number", 1)]
        ]