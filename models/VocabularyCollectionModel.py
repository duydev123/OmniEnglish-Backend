import datetime
from typing import List, Optional
from beanie import Document, Link
from pydantic import Field

class VocabularyCollectionModel(Document):
    title: str = Field(..., min_length=3)     
    description: Optional[str] = None
    topic: str = Field(..., min_length=3)        
    
    words: List[str] = Field(default=[])
    
    created_at: datetime = Field(default_factory=datetime.UTC)

    class Settings:
        name = "vocabulary_collections"


class UserWordHeartModel(Document):
    user_id: str = Field(..., min_length=1)  
    word: str = Field(..., min_length=1)    
    created_at: datetime = Field(default_factory=datetime.UTC) 
    status: bool

    class Settings:
        name = "user_word_hearts"
        indexes = [
            [("user_id", 1), ("word", 1)]
        ]

class UserProgressModel(Document):
    user_id: str = Field(..., min_length=1)
    collection_id: Link[VocabularyCollectionModel]
    mastered_words: List[str] = Field(default=[])
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    study_time_seconds: int = Field(default=0)
    
    class Settings:
        name = "user_progresses"
        indexes = [
            [("user_id", 1), ("collection_id", 1)] 
        ]