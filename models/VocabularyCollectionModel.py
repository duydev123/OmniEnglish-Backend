from datetime import datetime, UTC
from enum import Enum
from typing import List, Optional
from beanie import Document, Link
from pydantic import Field
from Paragraph import WordModel



class WordLearningStatus(str, Enum):
    LEARNING = "LEARNING"         
    MASTERED = "MASTERED"         
    NEEDS_REVIEW = "NEEDS_REVIEW" 


class VocabularyCollectionModel(Document):
    title: str = Field(..., min_length=3)     
    description: Optional[str] = None
    topic: str = Field(..., min_length=3)        
    language: str = Field(default="en-US")
    
    words: List[str] = Field(default=[])        
    custom_words: List[Link[WordModel]] = Field(default=[]) 
    

    is_official: bool = Field(default=False)    
    is_public: bool = Field(default=True)      
    total_learners: int = Field(default=0)      
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "vocabulary_collections"



class UserWordStatusModel(Document):
    user_id: str = Field(..., min_length=1)
    collection_id: Link[VocabularyCollectionModel]
    word: str = Field(..., min_length=1)
    

    status: WordLearningStatus = Field(default=WordLearningStatus.LEARNING)
    
    last_reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_word_statuses"
        indexes = [
            [("user_id", 1), ("collection_id", 1), ("word", 1)]
        ]


class UserProgressModel(Document):
    user_id: str = Field(..., min_length=1)
    collection_id: Link[VocabularyCollectionModel]
    

    accuracy_percentage: float = Field(default=0.0)    
    previous_week_accuracy: float = Field(default=0.0)   
    study_time_seconds: int = Field(default=0)      
    last_studied_at: Optional[datetime] = None        
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    class Settings:
        name = "user_progresses"
        indexes = [
            [("user_id", 1), ("collection_id", 1)] 
        ]