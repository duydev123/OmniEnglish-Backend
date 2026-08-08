from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Các Schema phụ để ẩn đáp án đúng đi ---
class HeadingMatchingResponse(BaseModel):
    order: int
    headings: List[str]  # Danh sách headings đã xáo trộn
    paragraphs: List[str]  # Nội dung các paragraph cần ghép heading
class FillBlankResponse(BaseModel):
    order: int
    passage_text: str  # Đoạn văn với placeholder [blank_1], [blank_2], ...
    blanks: List[str]  # Danh sách ID các ô trống: ["blank_1", "blank_2"]
    case_sensitive: bool
class TrueFalseNotGivenResponse(BaseModel):
    order: int
    statements: List[str]  # Danh sách các câu phát biểu
    # KHÔNG trả về đáp án đúng
class MultipleChoiceResponse(BaseModel):
    id: str # Lấy string ID của record
    order: int
    question_text: str
    options: List[str] # [A, B, C, D]
    # KHÔNG trả về correct_answer

# --- Schema Chính Trả Về (Response) ---
class ReadingSessionStartResponse(BaseModel):
    session_id: str
    
    # 1. Phần Passage[cite: 15]
    title: str
    content: str
    image_url: Optional[str] = None
    learning_tip: Optional[str] = None
    
    # 2. Phần Tiến độ (Progress)[cite: 15]
    completed_questions: int
    total_questions: int
    time_remaining_seconds: int
    
    # 3. Phần Câu hỏi (Đã giấu đáp án)[cite: 15]
    multiple_choices: List[MultipleChoiceResponse]
    heading_matchings: List[HeadingMatchingResponse]
    fill_blanks: List[FillBlankResponse]
    true_false_not_given: List[TrueFalseNotGivenResponse]  
    user_answers: Dict[str, str] = Field(default_factory=dict)







    # --- Schema Nhận Vào (Request) ---
class ReadingDraftRequest(BaseModel):
    time_remaining_seconds: int = Field(..., ge=0)
    
    # Format: {"mc_id_1": "Traditional office spaces", "blank_1": "cloud-based"}
    user_answers: Dict[str, str] = Field(default_factory=dict)









    # --- Schema Nhận Vào (Request) ---
# Tương tự như Draft, dùng chung data gửi lên
class ReadingSubmitRequest(ReadingDraftRequest):
    pass

# --- Schema phụ cho kết quả chi tiết ---
class QuestionResult(BaseModel):
    is_correct: bool
    user_answer: str
    correct_answer: str
    statement: Optional[str] = Field(default=None, description="Nội dung câu hỏi (cho True/False/Not Given)")
    options: Optional[List[str]] = None
    explanation: Optional[str] = None
    excerpt: Optional[str] = None

# --- Schema Trả Về (Response) ---
class ReadingSubmitResponse(BaseModel):
    status: str = "COMPLETED"
    score: int
    total_questions: int
    accuracy_rate: float
    
    # Chi tiết để Frontend tô màu Xanh/Đỏ
    detailed_results: Dict[str, QuestionResult]


# --- DTOs mới cho các Endpoint 5 -> 12 ---

# 5. Thông tin Session
class ReadingSessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    passage_id: str
    passage_title: Optional[str] = None
    completed_questions: int
    total_questions: int
    time_remaining_seconds: int
    score: int
    status: str
    user_answers: Dict[str, str]
    start_at: Optional[str] = None
    updated_at: Optional[str] = None


# 6. Danh sách Passages (Phân trang)
class PassageSummaryResponse(BaseModel):
    id: str
    title: str
    topic: str
    time_limit_minutes: int
    total_questions: int
    image_url: Optional[str] = None
    learning_tip: Optional[str] = None
    created_at: Optional[str] = None
    question_types: List[str] = Field(default_factory=list)


class PassageListResponse(BaseModel):
    items: List[PassageSummaryResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# 7. Chi tiết Passage
class PassageDetailResponse(BaseModel):
    id: str
    title: str
    topic: str
    content: str
    image_url: Optional[str] = None
    time_limit_minutes: int
    total_questions: int
    learning_tip: Optional[str] = None
    created_at: Optional[str] = None


# 8. Lịch sử làm bài của User
class UserHistoryItemResponse(BaseModel):
    session_id: str
    passage_id: str
    passage_title: str
    score: int
    total_questions: int
    accuracy_rate: float
    status: str
    attempt_number: int
    completed_questions: int = 0
    start_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserHistoryListResponse(BaseModel):
    items: List[UserHistoryItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# 10. Thống kê tổng quan của User
class UserReadingStatsResponse(BaseModel):
    total_sessions_completed: int
    average_accuracy_rate: float
    highest_score: int
    lowest_score: int
    skills_to_improve: List[str]
    total_xp: int


# 11. Review bài đã làm
class ReadingSessionReviewResponse(BaseModel):
    session_id: str
    passage_id: str
    passage_title: str
    passage_content: str
    score: int
    total_questions: int
    accuracy_rate: float
    status: str
    detailed_results: Dict[str, QuestionResult]


# 12. Bookmark từ vựng
class ReadingVocabularyBookmarkRequest(BaseModel):
    word: str = Field(..., min_length=1)
    context: Optional[str] = None


class ReadingVocabularyBookmarkResponse(BaseModel):
    success: bool = True
    message: str
    id: str
    session_id: str
    word: str
    context: Optional[str] = None
    created_at: Optional[str] = None