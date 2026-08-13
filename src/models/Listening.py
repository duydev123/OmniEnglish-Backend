# models/Listening.py
from datetime import datetime, UTC
from typing import Dict, List, Optional, Literal, Any
from beanie import Document, Link, PydanticObjectId
from pydantic import Field, BaseModel

# ==========================================
# 1. BẢNG ĐỀ THI & TRANSCRIPT (Gốc)
# ==========================================
class ListeningPassageModel(Document):
    title: str = Field(..., min_length=3)
    unit_code: Optional[str] = None
    audio_url: str = Field(..., min_length=1)
    
    interactive_transcript: List[Dict[str, str]] = Field(default_factory=list)
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
# 2. CÂU HỎI CHO COMPREHENSION
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

# ==========================================
# 3. MODEL LÀM BÀI COMPREHENSION (NGHE HIỂU)
# ==========================================
class UserAnswer(BaseModel):
    question_id: PydanticObjectId
    question_type: Literal["MULTIPLE_CHOICE", "COMPLETION"]
    answer: Any
    is_correct: Optional[bool] = None

class ListeningResult(BaseModel):
    score: float = 0
    accuracy_rate: float = 0
    xp_earned: int = 0
    competency_matrix: Dict[str, float] = Field(default_factory=dict)
    detailed_question_review: List[Dict] = Field(default_factory=list)

class UserListeningSessionModel(Document):
    user_id: str
    passage_id: Link[ListeningPassageModel]
    session_type: Literal["COMPREHENSION"] = "COMPREHENSION"
    status: Literal["IN_PROGRESS", "COMPLETED"] = "IN_PROGRESS"
    
    user_answers: List[UserAnswer] = Field(default_factory=list)
    time_remaining_seconds: int = 0
    result: Optional[ListeningResult] = None
    
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_listening_sessions"
        indexes = [
            [("user_id", 1), ("passage_id", 1)]
        ]

# ==========================================
# 4. MODEL LÀM BÀI DICTATION (CHÉP CHÍNH TẢ)
# ==========================================
class DictationSentenceHistory(BaseModel):
    transcript_index: int
    user_typed_text: str
    is_correct: bool = False
    accuracy_rate: float = 0.0
    correct_words: int = 0
    missed_contractions: int = 0
    transcript_comparison: List[Dict] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class UserDictationSessionModel(Document):
    user_id: str
    passage_id: Link[ListeningPassageModel]
    status: Literal["IN_PROGRESS", "COMPLETED"] = "IN_PROGRESS"
    
    # Key là string của transcript_index (VD: "0", "1")
    sentence_histories: Dict[str, DictationSentenceHistory] = Field(default_factory=dict)
    
    total_accuracy_rate: float = 0.0
    total_words_typed: int = 0
    
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_dictation_sessions"
        indexes = [
            [("user_id", 1), ("passage_id", 1)]
        ]