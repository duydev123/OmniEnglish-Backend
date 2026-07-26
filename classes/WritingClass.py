from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Schema Trả Về (Response) ---
class WritingPromptResponse(BaseModel):
    id: str
    title: str                                     # VD: "Impact of Artificial Intelligence..."
    task_type: str                                 # "TASK_1" hoặc "TASK_2"
    task_description: str                          # Đề bài chi tiết
    reference_image_url: Optional[str] = None      # Ảnh tham chiếu (nếu có)[cite: 19]
    ref_id: Optional[str] = None                   # VD: "ARCH-204-URB"[cite: 19]
    
    time_limit_minutes: int                        # Thời gian làm bài (phút)[cite: 19]
    word_count_target: int                         # Số từ mục tiêu (VD: 250)[cite: 19]
    
    # Gợi ý hỗ trợ người viết ở cột bên phải UI
    suggested_structure: List[Dict[str, str]]       # [{"section": "Introduction", "guide": "..."}][cite: 19]
    advanced_vocabulary: List[str]                 # ["Juxtaposition", "Obsolescence", ...][cite: 19]







    # --- Schema Nhận Vào (Request) ---
class WritingDraftRequest(BaseModel):
    essay_content: str                             # Nội dung bài viết đang soạn thảo[cite: 19]
    word_count: int = Field(default=0, ge=0)       # Số từ hiện tại[cite: 19]
    time_spent_seconds: int = Field(default=0, ge=0) # Thời gian đã gõ bài[cite: 19]

# --- Schema Trả Về (Response) ---
class WritingDraftResponse(BaseModel):
    session_id: str
    status: str = "DRAFT"                          # Trạng thái DRAFT[cite: 19]
    message: str = "Draft saved successfully"









    # --- Schemas Phụ Trả Về Cho Báo Cáo REVIEW ---
class HighlightSpan(BaseModel):
    text: str                                      # Từ/Cụm từ bị gạch chân[cite: 19]
    type: str                                      # "GRAMMAR", "WORD_CHOICE", "ADVANCED_LEXIS"[cite: 19]
    feedback_index: int                            # Trỏ tới index tương ứng trong danh sách feedback[cite: 19]

class DetailedFeedback(BaseModel):
    type: str                                      # Loại lỗi[cite: 19]
    original: str                                  # Cụm gốc bị sai[cite: 19]
    correction: str                                # Cụm đúng sửa lại[cite: 19]
    explanation: str                               # Giải thích chi tiết từ AI[cite: 19]

class ImprovementComparison(BaseModel):
    category: str                                  # "Grammar", "Vocabulary"...[cite: 19]
    original: str                                  # "technology improve"[cite: 19]
    improved: str                                  # "technology improves"[cite: 19]

class Milestone(BaseModel):
    date: str                                      # "Oct 15"[cite: 19]
    title: str                                     # "Achieved C1 Vocabulary"[cite: 19]


# --- Schema Trả Về Chính (Response) ---
class WritingSubmitResponse(BaseModel):
    session_id: str
    status: str = "REVIEWED"                       # DRAFT -> SUBMITTED -> REVIEWED[cite: 19]
    topic_title: str                               #[cite: 19]
    essay_content: str                             #[cite: 19]
    word_count: int                                #[cite: 19]
    time_spent_seconds: int                        #[cite: 19]
    
    # 1. Điểm số Tổng & 4 Tiêu chí IELTS[cite: 19]
    overall_score: int                             # VD: 75 Score[cite: 19]
    potential_score: Optional[int] = None          # Điểm tiềm năng (VD: 88)[cite: 19]
    general_summary: Optional[str] = None          # Nhận xét tổng quan[cite: 19]
    
    task_achievement_score: float                  # VD: 8.5/9.0[cite: 19]
    lexical_resource_score: float                  # VD: 7.5/9.0[cite: 19]
    grammar_accuracy_score: float                  # VD: 6.5/9.0[cite: 19]
    coherence_cohesion_score: float                # VD: 7.0/9.0[cite: 19]

    # 2. Render Highlight màu trên bài essay[cite: 19]
    highlight_spans: List[HighlightSpan]           #[cite: 19]

    # 3. Chi tiết Feedback cột bên phải UI[cite: 19]
    detailed_feedbacks: List[DetailedFeedback]     #[cite: 19]
    
    # 4. Bảng so sánh nâng cấp & Lịch sử cột mốc[cite: 19]
    improvements_comparison: List[ImprovementComparison] #[cite: 19]
    achieved_milestones: List[Milestone]           #[cite: 19]