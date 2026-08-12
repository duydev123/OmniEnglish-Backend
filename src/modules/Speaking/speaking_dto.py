from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from models.Speaking import WordDetail

# ==========================================
# 1. QUẢN LÝ CHỦ ĐỀ & CÂU HỎI (TOPICS & PROMPTS)
# ==========================================

class SpeakingTopicSummaryResponse(BaseModel):
    id: str
    title: str                                     # VD: "IELTS Speaking Mock Test 1"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_full_test: bool
    # Có thể thêm số lượng câu hỏi nếu cần
    prompt_count: Optional[int] = 0

class SpeakingPromptResponse(BaseModel):
    id: str
    topic_id: str
    part: str                                      # "PART_1", "PART_2", "PART_3", "SHADOWING"
    sub_topic: Optional[str] = None
    question_text: str                             
    examiner_audio_url: Optional[str] = None       # Link audio giám khảo đọc câu hỏi
    
    # Gợi ý hiển thị UI
    useful_vocabulary: List[str] = Field(default_factory=list)
    ielts_tips: List[str] = Field(default_factory=list)
    examiner_tip: Optional[str] = None
    response_structure: List[Dict[str, str]] = Field(default_factory=list)

# ==========================================
# 2. SESSION START & PROGRESS (LÀM BÀI)
# ==========================================

class SpeakingSessionStartResponse(BaseModel):
    session_id: str
    topic_id: Optional[str] = None
    prompt_id: Optional[str] = None
    test_type: str                                 # "PART_1", "FULL_TEST"...
    status: str = "IN_PROGRESS"
    
    # Nếu bắt đầu 1 câu, trả về luôn câu hỏi đó
    current_prompt: Optional[SpeakingPromptResponse] = None

# Request nộp audio (Nếu dùng JSON thay vì Form data, tuy nhiên hiện tại Controller đang dùng UploadFile/Form)
class SpeakingSegmentSubmitRequest(BaseModel):
    prompt_id: str
    speaking_time_seconds: int = Field(default=0, ge=0)

class SpeakingSegmentSubmitResponse(BaseModel):
    session_id: str
    prompt_id: str
    status: str = "IN_PROGRESS"
    user_transcript: str       
    user_audio_url: Optional[str] = None                    
    segment_score: Optional[float] = None          
    pronunciation_score: Optional[float] = None    
    fluency_score: Optional[float] = None        
    lexical_score: Optional[float] = None          # THÊM MỚI
    grammar_score: Optional[float] = None          # THÊM MỚI  
    realtime_feedback: Optional[str] = None
    words_detail: List[WordDetail] = Field(default_factory=list)
    next_prompt_id: Optional[str] = None


# ==========================================
# 3. SUB-SCHEMAS CHO KẾT QUẢ ĐÁNH GIÁ (REVIEW)
# ==========================================

class KeyStrength(BaseModel):
    title: str                                     
    desc: str                                      

class AreaForGrowth(BaseModel):
    category: str                                  # "PRONUNCIATION", "GRAMMAR", "LEXICAL", "FLUENCY"
    title: str                                     
    desc: str                                      
    tip: str                                       
    incorrect: str                                 
    correct: str                                   

class QuestionDetailReview(BaseModel):
    question_text: str                             
    user_transcript: str                           # Bóc băng + highlight
    user_audio_url: Optional[str] = None           # Audio đoạn ghi âm này

class Milestone(BaseModel):
    title: str
    tasks: List[str]

# ==========================================
# 4. HOÀN THÀNH & XEM CHI TIẾT SESSIONS
# ==========================================

class SpeakingSubmitResponse(BaseModel):
    session_id: str
    status: str = "COMPLETED"
    message: str = "Speaking test evaluated successfully"

class SpeakingSessionDetailResponse(BaseModel):
    session_id: str
    test_type: str                                 
    title: str                                     
    duration_str: str                              
    status: str                                    
    full_session_audio_url: Optional[str] = None
    
    # --- Điểm số ---
    overall_band_score: float                      
    band_score_delta: float                        
    percentile_rank: Optional[str] = None          
    
    pronunciation_score: float                     
    fluency_score: float                           
    lexical_score: float                           
    grammar_score: float                           
    
    # --- Phân tích ---
    key_strengths: List[KeyStrength]               
    areas_for_growth: List[AreaForGrowth]          
    questions_detail: List[QuestionDetailReview]   
    
    # --- AI Insights ---
    ai_insights_summary: Optional[str] = None      
    detailed_criteria_feedback: List[Dict]         
    next_milestone: Optional[Milestone] = None     
    recommended_resources: List[Dict[str, str]]    
    
    created_at: datetime

# ==========================================
# 5. LỊCH SỬ HỌC TẬP (HISTORY)
# ==========================================

class SpeakingHistoryItemResponse(BaseModel):
    session_id: str
    test_type: str
    title: str
    overall_band_score: float
    duration_str: str
    status: str
    created_at: datetime
    
    
#====shadowing 
# DTO trả về thông tin câu Shadowing
class ShadowingSentenceResponse(BaseModel):
    id: str
    target_skill: str
    english_text: str
    ipa_text: str
    audio_url: Optional[str] = None

# DTO trả về kết quả chấm điểm (Không lưu lịch sử)
class ShadowingEvaluateResponse(BaseModel):
    accuracy_score: float
    fluency_score: float
    user_transcript: str
    words_detail: List[WordDetail] = Field(default_factory=list)