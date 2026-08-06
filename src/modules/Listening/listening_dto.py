# modules/Listening/listening_dto.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from models.Listening import UserAnswer

# --- CÁC SCHEMA CƠ BẢN ---
class TranscriptLine(BaseModel):
    start_time: str                                     
    end_time: str                                       
    en: str                                             
    vi: str                                         

class KeyVocabularyItem(BaseModel):
    word: str                                           
    meaning: str                                    

class ListeningMultipleChoiceResponse(BaseModel):
    id: str
    order: int                                          
    question_text: str                                  
    options: List[str]                              

class ListeningCompletionResponse(BaseModel):
    id: str
    order: int                                          
    template_text: str                                  
    case_sensitive: bool                             

# --- PASSAGES & HISTORY DTO ---
class ListeningPassageSummaryResponse(BaseModel):
    id: str
    title: str
    unit_code: Optional[str] = None
    time_limit_minutes: int
    total_questions: int

class ListeningHistoryItemResponse(BaseModel):
    session_id: str
    passage_id: str
    passage_title: str
    session_type: str  
    status: str
    accuracy_rate: float
    submitted_at: Optional[datetime] = None


# ==========================================
# DTO CHO COMPREHENSION
# ==========================================
class ComprehensionSessionStartResponse(BaseModel):
    session_id: str
    passage_id: str
    session_type: str = "COMPREHENSION"
    title: str                                          
    unit_code: Optional[str] = None                     
    audio_url: str                                      
    time_limit_minutes: int                                  
    completed_questions: int                            
    total_questions: int                                     
    multiple_choices: List[ListeningMultipleChoiceResponse]
    completions: List[ListeningCompletionResponse]

class ListeningDraftRequest(BaseModel):
    user_answers: List[UserAnswer] = Field(default_factory=list)           
    time_remaining_seconds: int = Field(default=0, ge=0)        

class ListeningDraftResponse(BaseModel):
    session_id: str
    status: str = "IN_PROGRESS"                         
    message: str = "Draft saved successfully"

class QuestionReviewDetail(BaseModel):
    question_text: str
    your_answer: Any                                
    correct_answer: Any                             
    is_correct: bool
    timestamp_clip: Optional[str] = None                 
    learning_hint: Optional[str] = None              

class ListeningSubmitResponse(BaseModel):
    session_id: str
    session_type: str = "COMPREHENSION"                                  
    status: str = "COMPLETED"                                
    accuracy_rate: float                                
    score_summary: Optional[str] = None                 
    xp_earned: int                                           
    competency_matrix: Dict[str, float] = Field(default_factory=dict)           
    detailed_question_review: List[QuestionReviewDetail] = Field(default_factory=list)          


# ==========================================
# DTO CHO DICTATION
# ==========================================
class DictationSessionStartResponse(BaseModel):
    session_id: str
    passage_id: str
    session_type: str = "DICTATION"
    title: str                                          
    audio_url: str                                      
    time_limit_minutes: int                                  
    interactive_transcript: List[TranscriptLine]        
    key_vocabulary: List[KeyVocabularyItem]                   
    total_questions: int

class TranscriptComparisonWord(BaseModel):
    word: str                                           
    user_word: Optional[str] = None                     
    is_correct: bool       

class DictationSentenceGradeRequest(BaseModel):
    transcript_index: int = Field(..., description="Vị trí của câu trong mảng interactive_transcript")
    user_typed_text: str = Field(..., description="Nội dung user gõ")

class DictationSentenceGradeResponse(BaseModel):
    is_correct: bool
    accuracy_rate: float
    words_typed: int
    correct_words: int
    missed_contractions: int
    transcript_comparison: List[TranscriptComparisonWord] = Field(default_factory=list)