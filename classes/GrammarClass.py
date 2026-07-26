from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Schemas phụ cho Grammar Guide (Cột bên phải UI) ---
class GrammarQuickReference(BaseModel):
    pronoun: str                                   # VD: "Who"
    use_for: str                                   # VD: "People"

class GrammarGuideResponse(BaseModel):
    rule_title: Optional[str] = None               # VD: "Defining vs. Non-Defining"
    rule_description: Optional[str] = None         # Mô tả quy tắc
    formula: Optional[str] = None                  # VD: "Subject + Relative Pronoun + Verb"[cite: 11]
    quick_reference: List[GrammarQuickReference]  # Bảng Quick Reference[cite: 11]

# --- Schema phụ cho từng câu hỏi (Đã giấu correct_answer) ---
class GrammarQuestionResponse(BaseModel):
    id: str
    question_type: str                             # "MULTIPLE_CHOICE", "FILL_IN_BLANK", "ERROR_IDENTIFICATION", "WORD_FORM"[cite: 11]
    question_text: str                             # Nội dung câu hỏi[cite: 11]
    context_image_url: Optional[str] = None        # Ảnh minh họa Scenario Focus / Context[cite: 11]
    scenario_focus_title: Optional[str] = None     # VD: "Corporate Achievement"[cite: 11]
    
    # Dành riêng cho Error Identification (Phần gạch chân A, B, C, D)
    underlined_options: List[Dict[str, str]] = Field(default_factory=list) # [{"key": "A", "text": "..."}, ...][cite: 11]
    
    # Dành riêng cho Word Form
    base_word: Optional[str] = None                # VD: "SUCCESS"[cite: 11]
    
    # Dành cho Trắc nghiệm
    options: List[str] = Field(default_factory=list) # Các lựa chọn A, B, C, D[cite: 11]
    
    # Mẹo & Gợi ý trên UI
    grammar_tip: Optional[str] = None              # Box "Did you know?" hoặc "Learning Tips"[cite: 11]
    hint_text: Optional[str] = None                # Nút "Get a Hint"[cite: 11]
    recommended_path_title: Optional[str] = None   # Learning Path đề xuất[cite: 11]

# --- Schema Chính Trả Về (Response) ---
class GrammarSessionStartResponse(BaseModel):
    session_id: str
    topic_id: str
    title: str                                     # VD: "Grammar: Conditionals" hoặc "Relative Clauses"[cite: 11]
    level: str                                     # VD: "Intermediate B2"[cite: 11]
    
    # Cột lý thuyết Grammar Guide
    guide: GrammarGuideResponse
    # Tiến độ
    completed_tasks: int                           # VD: Task 4 of 12[cite: 11]
    total_tasks: int                               # VD: 12[cite: 11]
    
    # Danh sách câu hỏi
    questions: List[GrammarQuestionResponse]


# --- Schema Nhận Vào (Request) ---
class GrammarDraftRequest(BaseModel):
    practice_time_seconds: int = Field(default=0, ge=0) #[cite: 11]
    
    # Format: {"q_id_1": "C", "q_id_2": "success", "q_id_3": "who"}
    user_answers: Dict[str, str] = Field(default_factory=dict) #[cite: 11]

# --- Schema Trả Về (Response) ---
class GrammarDraftResponse(BaseModel):
    session_id: str
    status: str = "IN_PROGRESS"                    #[cite: 11]
    message: str = "Draft saved successfully"


# --- Schema phụ cho kết quả câu hỏi ---
class QuestionAnswerResult(BaseModel):
    is_correct: bool
    user_answer: str
    correct_answer: str
    explanation_tip: Optional[str] = None          # Giải thích chi tiết đáp án[cite: 11]

# --- Schema Trả Về Chính (Response) ---
class GrammarSubmitResponse(BaseModel):
    session_id: str
    status: str = "COMPLETED"                      #[cite: 11]
    
    score: int                                     # Số câu đúng[cite: 11]
    total_tasks: int                               # Tổng số câu[cite: 11]
    accuracy_rate: float                           # VD: 92%[cite: 11]
    xp_earned: int                                 # VD: +12 XP[cite: 11]
    practice_time_seconds: int                     # Session Time (VD: 842s)[cite: 11]
    
    # Chi tiết đúng/sai từng câu để Frontend render UI Xanh/Đỏ
    detailed_results: Dict[str, QuestionAnswerResult]