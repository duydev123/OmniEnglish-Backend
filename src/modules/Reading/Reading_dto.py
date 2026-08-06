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

# --- Schema Trả Về (Response) ---
class ReadingSubmitResponse(BaseModel):
    status: str = "COMPLETED" #[cite: 15]
    score: int                #[cite: 15]
    total_questions: int      #[cite: 15]
    accuracy_rate: float
    
    # Chi tiết để Frontend tô màu Xanh/Đỏ
    # Format: {"mc_id_1": {"is_correct": True, "user_answer": "...", "correct_answer": "..."}}
    detailed_results: Dict[str, QuestionResult]