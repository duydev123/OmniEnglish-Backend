from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Schema Trả Về (Response) ---
class SpeakingPromptResponse(BaseModel):
    id: str
    part: str                                      # "PART_1", "PART_2", "PART_3"
    topic: str                                     # VD: "Hometown & Studies"[cite: 16]
    question_text: str                             # Câu hỏi hoặc chủ đề mở đầu[cite: 16]
    
    # Dành riêng cho Part 2 Cue Card (nếu có)
    candidate_card_bullet_points: List[str] = Field(default_factory=list)
    
    # Gợi ý hỗ trợ người nói ở Cột Bên Phải UI
    useful_vocabulary: List[str]                   # ["Metropolis", "Bustling city", ...][cite: 16]
    ielts_tips: List[str]                          # Mẹo ghi điểm[cite: 16]
    examiner_tip: Optional[str] = None             # Tip riêng từ giám khảo[cite: 16]
    response_structure: List[Dict[str, str]]       # Khung câu trả lời gợi ý[cite: 16]






# --- Schema Nhận Vào (Request) ---
class SpeakingSegmentSubmitRequest(BaseModel):
    test_type: str = Field(..., pattern="^(PART_1|PART_2|PART_3|SHADOWING)$")
    question_text: str                             # Câu hỏi user đang trả lời[cite: 16]
    user_audio_url: str                            # URL file ghi âm giọng user[cite: 16]
    user_transcript: str                           # Chữ AI nhận diện từ giọng nói[cite: 16]
    user_notes: Optional[str] = None               # Note nháp Part 2 (nếu có)[cite: 16]
    speaking_time_seconds: int = Field(default=0, ge=0)

# --- Schema Trả Về (Response) ---
class SpeakingSegmentSubmitResponse(BaseModel):
    session_id: str
    status: str = "IN_PROGRESS"
    segment_score: float                           # Điểm sơ bộ câu này[cite: 16]
    realtime_feedback: str                         # Nhận xét nhanh



# --- Schemas Phụ Trả Về Cho Báo Cáo REVIEW ---
class KeyStrength(BaseModel):
    title: str                                     # VD: "Effective Collocations"[cite: 16]
    desc: str                                      # Mô tả điểm mạnh[cite: 16]

class AreaForGrowth(BaseModel):
    category: str                                  # "PRONUNCIATION", "GRAMMAR"...[cite: 16]
    title: str                                     # VD: "Ending Sounds: /d/"[cite: 16]
    desc: str                                      # Mô tả chi tiết[cite: 16]
    tip: str                                       # Mẹo sửa lỗi[cite: 16]
    incorrect: str                                 # VD: "how to applied"[cite: 16]
    correct: str                                   # VD: "how to apply"[cite: 16]

class QuestionDetailReview(BaseModel):
    question_text: str                             #[cite: 16]
    user_transcript: str                           # Đoạn văn bản có tô màu từ đúng/lỗi[cite: 16]
    user_audio_url: Optional[str] = None           # Audio riêng câu này[cite: 16]

# --- Schema Trả Về Chính (Response) ---
class SpeakingSubmitResponse(BaseModel):
    session_id: str
    test_type: str                                 # "PART_1", "PART_2", "PART_3"[cite: 16]
    title: str                                     # VD: "Speaking Part 1: Result Analysis"[cite: 16]
    duration_str: str                              # VD: "02:45"[cite: 16]
    status: str = "COMPLETED"                      #[cite: 16]
    
    # 1. Điểm số Tổng & So sánh
    overall_band_score: float                      # VD: 7.5[cite: 16]
    band_score_delta: float                        # VD: +0.5[cite: 16]
    percentile_rank: Optional[str] = None          # VD: "Top 15% User"[cite: 16]

    # 2. Điểm 4 Tiêu chí IELTS[cite: 16]
    pronunciation_score: float                     # VD: 8.0/10[cite: 16]
    fluency_score: float                           # VD: 7.2/10[cite: 16]
    lexical_score: float                           # VD: 7.5/10[cite: 16]
    grammar_score: float                           # VD: 7.0/10[cite: 16]

    # 3. Phân tích Chi tiết (Cột bên trái UI)[cite: 16]
    key_strengths: List[KeyStrength]               #[cite: 16]
    areas_for_growth: List[AreaForGrowth]          #[cite: 16]
    questions_detail: List[QuestionDetailReview]   #[cite: 16]

    # 4. AI Insights & Cột mốc tiếp theo (Cột bên phải UI)[cite: 16]
    ai_insights_summary: Optional[str] = None      # Nhận xét tổng quan AI[cite: 16]
    detailed_criteria_feedback: List[Dict]         # Phân tích sâu 4 tiêu chí[cite: 16]
    next_milestone: Optional[Dict] = None          # Target tiếp theo[cite: 16]
    recommended_resources: List[Dict[str, str]]    # Tài liệu đề xuất[cite: 16]