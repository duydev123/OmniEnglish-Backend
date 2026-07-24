from datetime import datetime
from typing import Dict, List, Optional
from beanie import Document
from pydantic import Field

class UserFreeSpeakingModel(Document):
    user_id: str = Field(..., min_length=1)

    topic: str = Field(..., min_length=3)

    user_transcript: str = Field(..., min_length=1) 
    
    overall_score: float = Field(..., ge=0, le=10)      
    pronunciation_score: float = Field(default=0, ge=0, le=10)
    fluency_score: float = Field(default=0, ge=0, le=10)       
    lexical_score: float = Field(default=0, ge=0, le=10)    
    grammar_score: float = Field(default=0, ge=0, le=10)      


    highlight_words: List[Dict[str, str]] = Field(default=[])

    ai_feedback: Optional[str] = None
    suggested_improvements: List[str] = Field(default=[]) 
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_free_speakings"
        indexes = [
            [("user_id", 1), ("created_at", -1)]
        ]



class UserSpeakingHistoryModel(Document):
    user_id: str = Field(..., min_length=1)
    

    target_type: str = Field(..., regex="^(word|sentence|paragraph)$")
    

    target_id: str = Field(..., min_length=1)
    

    accuracy_score: int = Field(..., ge=0, le=100) 
    fluency_score: int = Field(..., ge=0, le=100)   
    status: str = Field(default="NEEDS REVIEW") 
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_speaking_histories"
        indexes = [
            [("user_id", 1), ("created_at", -1)]
        ]