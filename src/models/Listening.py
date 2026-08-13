from datetime import datetime, UTC
from typing import Dict, List, Optional, Union
from beanie import Document, Link, PydanticObjectId
from pydantic import Field, BaseModel


# ==========================================
# 1. BẢNG DỮ LIỆU ĐỀ THI & TRANSCRIPT (Gốc do Admin/System tạo)
# ==========================================
class ListeningPassageModel(Document):
    title: str = Field(..., min_length=3)                     # VD: "FIRST SNOWFALL" hoặc "Business Negotiation"
    unit_code: Optional[str] = None                           # VD: "UNIT04"
    audio_url: str = Field(..., min_length=1)                 # URL file mp3/audio
    
    # BỔ SUNG BẢN TRANSCRIPT SONG NGỮ (Cho Màn hình Full Transcript Interactive)
    # Example item: {
    #    "start_time": "0:03", 
    #    "end_time": "0:08", 
    #    "en": "Today is November 26th.", 
    #    "vi": "Hôm nay là ngày 26 tháng 11."
    # }
    interactive_transcript: List[Dict[str, str]] = Field(default_factory=list)
    
    # Key Vocabulary
    key_vocabulary: List[Dict[str, str]] = Field(default_factory=list)
    
    time_limit_minutes: int = Field(default=15)               
    total_questions: int = Field(default=20)                  

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "listening_passages"


class ListeningAudioSegmentModel(Document):
    passage_id: Link[ListeningPassageModel]
    audio_file_url: Optional[str] = None
    start_time_ms: int
    end_time_ms: int
    transcript: str
    transcript_json: Optional[List[Dict]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "listening_audio_segments"


# ==========================================
# 2. CÁC DẠNG CÂU HỎI LISTENING
# ==========================================
class ListeningMultipleChoiceModel(Document):
    passage_id: Link[ListeningPassageModel]  
    order: int = Field(default=1)
    question_text: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=2)
    correct_answer: str = Field(..., min_length=1)
    
    # BỔ SUNG CHO BÁO CÁO REVIEW:
    timestamp_clip: Optional[str] = None                      # VD: "00:45" (Nút REPLAY CLIP)
    learning_hint: Optional[str] = None                       # Gợi ý bài học / giải thích đáp án
    competency_type: Optional[str] = None                     # "Global Understanding", "Inference & Tone"...
    audio_segment_id: Optional[Link[ListeningAudioSegmentModel]] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "listening_multiple_choices"


class ListeningCompletionModel(Document):
    passage_id: Link[ListeningPassageModel]  
    order: int = Field(default=2)
    template_text: str = Field(..., min_length=1)  
    correct_answers: Dict[str, str] = Field(...)
    case_sensitive: bool = Field(default=False)
    audio_segment_id: Optional[Link[ListeningAudioSegmentModel]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "listening_completions"


class UserAnswer(BaseModel):
    question_id: PydanticObjectId
    question_type: str
    answer: Union[str, Dict[str, str]]
    is_correct: bool


class ListeningResult(BaseModel):
    score: float
    accuracy_rate: float
    xp_earned: int
    competency_matrix: Dict[str, float]
    detailed_question_review: List[Dict] = Field(default_factory=list)


# ==========================================
# 3. BẢNG LƯU BÀI LÀM & BÁO CÁO REVIEW CỦA USER (Full Analytics)
# ==========================================
class UserListeningSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    passage_id: Link[ListeningPassageModel]
    
    # "COMPREHENSION" hoặc "DICTATION"
    session_type: str = Field(default="COMPREHENSION", pattern="^(COMPREHENSION|DICTATION)$")
    completed_questions: int = Field(default=0)
    # --- THỐNG KÊ CHUNG (Overall Stats) ---
    accuracy_rate: float = Field(default=0.0)                 # VD: 85% hoặc 95%
    score_summary: Optional[str] = None                       # VD: "17 out of 20 Correct"
    xp_earned: int = Field(default=0)                         # VD: +250 XP

    # --- ĐÀNH RIÊNG CHO CÂU HỎI LÝ THUYẾT (Analytics & Competency Matrix) ---
    # Breakdown: {"Global Understanding": 100, "Specific Information": 80, "Inference & Tone": 75}
    competency_matrix: Dict[str, float] = Field(default_factory=dict)
    
    # Details từng câu hỏi: [{ "q_id": "...", "your_answer": "...", "correct_answer": "...", "is_correct": true }]
    detailed_question_review: List[Dict] = Field(default_factory=list)

    # --- DÀNH RIÊNG CHO DICTATION (Chép chính tả Review) ---
    words_typed: int = Field(default=0)                       # VD: 158 words
    wpm: int = Field(default=0)                               # VD: 42 WPM
    missed_contractions: int = Field(default=0)               # VD: 2

    # Dữ liệu nháp cho cả comprehension và dictation
    user_answers: Union[List[UserAnswer], Dict[str, str]] = Field(default_factory=list)
    user_typed_text: Optional[str] = Field(default="")
    time_remaining_seconds: int = Field(default=0)
    score: float = Field(default=0.0)
    # Mảng so sánh từ gõ đúng/sai để tô màu Xanh/Đỏ trên UI:
    # Example: [{"word": "strategy", "user_word": "stratagy", "is_correct": false}]
    transcript_comparison: List[Dict] = Field(default_factory=list)
    
    spelling_tip: Optional[str] = None                        # Mẹo chính tả
    listening_insight: Optional[str] = None                   # Nhận xét AI

    status: str = Field(default="IN_PROGRESS")                # "IN_PROGRESS" -> "COMPLETED"
    result: Optional[ListeningResult] = None
    submitted_at: Optional[datetime] = None
    start_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_listening_sessions"
        indexes = [
            [("user_id", 1), ("passage_id", 1)]
        ]


class DictationSentenceHistory(BaseModel):
    transcript_index: int
    user_typed_text: str
    is_correct: bool
    accuracy_rate: float
    correct_words: int
    missed_contractions: int
    transcript_comparison: List[Dict] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserDictationSessionModel(Document):
    user_id: str = Field(..., min_length=1)
    passage_id: Link[ListeningPassageModel]
    status: str = Field(default="IN_PROGRESS")                # "IN_PROGRESS" -> "COMPLETED"
    sentence_histories: Dict[str, DictationSentenceHistory] = Field(default_factory=dict)
    total_accuracy_rate: float = Field(default=0.0)
    total_words_typed: int = Field(default=0)
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_dictation_sessions"
        indexes = [
            [("user_id", 1), ("passage_id", 1)]
        ]
