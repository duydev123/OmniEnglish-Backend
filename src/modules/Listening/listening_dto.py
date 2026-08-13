from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Các Schema phụ ---
class TranscriptLine(BaseModel):
    start_time: str                                # VD: "0:03"
    end_time: str                                  # VD: "0:08"
    en: str                                        # VD: "Today is November 26th."
    vi: str                                        # VD: "Hôm nay là ngày 26 tháng 11."

class KeyVocabularyItem(BaseModel):
    word: str                                      # VD: "Synthesize"[cite: 12]
    meaning: str                                   # VD: "To combine several things..."[cite: 12]

class ListeningMultipleChoiceResponse(BaseModel):
    id: str
    order: int                                     #[cite: 12]
    question_text: str                             #[cite: 12]
    options: List[str]                             # Cố tình giấu correct_answer[cite: 12]
    timestamp_clip: Optional[str] = None           #[cite: 12]

class ListeningCompletionResponse(BaseModel):
    id: str
    order: int                                     #[cite: 12]
    template_text: str                             #[cite: 12]
    case_sensitive: bool                            #[cite: 12]

class ListeningPassageSummary(BaseModel):
    id: str
    title: str
    unit_code: Optional[str] = None
    audio_url: str
    time_limit_minutes: int
    total_questions: int
    question_types: List[str] = Field(default_factory=list)

class ListeningPassageDetailResponse(BaseModel):
    id: str
    title: str
    unit_code: Optional[str] = None
    audio_url: str
    interactive_transcript: List[TranscriptLine] = Field(default_factory=list)
    key_vocabulary: List[KeyVocabularyItem] = Field(default_factory=list)
    time_limit_minutes: int
    total_questions: int
    created_at: Optional[str] = None

class ListeningPassageListResponse(BaseModel):
    items: List[ListeningPassageSummary]
    page: int
    limit: int
    total: int

# --- Schema Chính Trả Về (Response) ---
class ListeningSessionStartResponse(BaseModel):
    session_id: str
    passage_id: str
    title: str                                     # VD: "FIRST SNOWFALL"[cite: 12]
    unit_code: Optional[str] = None                # VD: "UNIT04"[cite: 12]
    audio_url: str                                 # Link MP3 bài nghe[cite: 12]
    time_limit_minutes: int                        #[cite: 12]
    
    # Dữ liệu cho giao diện Player & Tab Transcript
    interactive_transcript: List[TranscriptLine]   # Danh sách phụ đề Anh-Việt[cite: 12]
    key_vocabulary: List[KeyVocabularyItem]         # Sidebar Key Vocabulary[cite: 12]
    
    # Tiến độ
    completed_questions: int                       #[cite: 12]
    total_questions: int                           #[cite: 12]
    
    # Câu hỏi (Dành cho session_type = COMPREHENSION)
    multiple_choices: List[ListeningMultipleChoiceResponse]
    completions: List[ListeningCompletionResponse]
    user_answers: Dict[str, str] = Field(default_factory=dict)
    user_typed_text: Optional[str] = None
    time_remaining_seconds: int = Field(default=0)







    # --- Schema Nhận Vào (Request) ---
class ListeningDraftRequest(BaseModel):
    session_type: str = Field(default="COMPREHENSION", pattern="^(COMPREHENSION|DICTATION)$") #[cite: 12]
    
    # Dành cho Dictation:
    user_typed_text: Optional[str] = None          # Chữ user vừa chép chính tả[cite: 12]
    
    # Dành cho Comprehension:
    user_answers: Dict[str, str] = Field(default_factory=dict) # {"q_id": "answer"}[cite: 12]
    time_remaining_seconds: int = Field(default=0, ge=0)       #[cite: 12]

# --- Schema Trả Về (Response) ---
class ListeningDraftResponse(BaseModel):
    session_id: str
    status: str = "IN_PROGRESS"                    #[cite: 12]
    message: str = "Progress saved successfully"





# --- Schemas Phụ Trả Về Cho Báo Cáo ---
class QuestionReviewDetail(BaseModel):
    question_text: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    timestamp_clip: Optional[str] = None            # VD: "00:45" (Nút REPLAY CLIP)
    learning_hint: Optional[str] = None             # Gợi ý bài học/lỗi sai
    question_id: Optional[str] = None
    audio_url: Optional[str] = None
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    segment_transcript: Optional[str] = None

class TranscriptComparisonWord(BaseModel):
    word: str                                      # Từ đúng gốc
    user_word: Optional[str] = None                # Từ user đã gõ
    is_correct: bool                               # True (Xanh) / False (Đỏ)
    status: Optional[str] = None                   # "correct", "wrong", "missing"


# --- Schema Trả Về Chính (Response) ---
class ListeningSubmitResponse(BaseModel):
    session_id: str
    session_type: str                              # "COMPREHENSION" hoặc "DICTATION"[cite: 12]
    status: str = "COMPLETED"                      #[cite: 12]
    
    # 1. Thống kê chung[cite: 12]
    accuracy_rate: float                           # VD: 85% hoặc 95%[cite: 12]
    score_summary: Optional[str] = None            # VD: "17 out of 20 Correct"[cite: 12]
    xp_earned: int                                 # VD: +250 XP[cite: 12]
    
    # 2. Dành cho Comprehension Analytics Review[cite: 12]
    competency_matrix: Dict[str, float] = Field(default_factory=dict) 
    # {"Global Understanding": 100, "Specific Information Retrieval": 80, "Inference & Tone": 75}[cite: 12]
    
    detailed_question_review: List[QuestionReviewDetail] = Field(default_factory=list)
    
    # 3. Dành cho Dictation Review (Màn hình chép chính tả)[cite: 12]
    words_typed: int = 0                           # VD: 158 words[cite: 12]
    wpm: int = 0                                   # VD: 42 WPM[cite: 12]
    missed_contractions: int = 0                   # VD: 2[cite: 12]
    
    transcript_comparison: List[TranscriptComparisonWord] = Field(default_factory=list) # Tô màu Xanh/Đỏ
    spelling_tip: Optional[str] = None             # Mẹo chính tả
    listening_insight: Optional[str] = None        # Nhận xét AI
    audio_url: Optional[str] = None
    interactive_transcript: Optional[List[TranscriptLine]] = None