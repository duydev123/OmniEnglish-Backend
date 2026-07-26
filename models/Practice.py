from datetime import datetime, UTC
from beanie import Document
from pydantic import Field

class PracticeAttemptModel(Document):
    user_id: str = Field(..., min_length=1)
    

    module_type: str = Field(..., min_length=1) 
    

    practice_test_id: str = Field(..., min_length=1)


    score: int = Field(default=0)   
    total_questions: int = Field(default=0)   
    time_spent_seconds: int = Field(default=0) 
    

    status: str = Field(default="IN_PROGRESS") 
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "practice_attempts"
        indexes = [
            [("user_id", 1), ("module_type", 1), ("created_at", -1)]
        ]