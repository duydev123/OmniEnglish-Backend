

import datetime
from typing import Dict, List
from beanie import Document
from pydantic import Field



class ListeningMultipleChoiceModel(Document):
    passage_id: str = Field(..., min_length=1)  
    order: int = Field(default=1)
    question_text: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=2)
    correct_answer: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "listening_multiple_choices"


class ListeningCompletionModel(Document):
    passage_id: str = Field(..., min_length=1)  #!
    order: int = Field(default=2)
    template_text: str = Field(..., min_length=1)  
    correct_answers: Dict[str, str] = Field(...)
    case_sensitive: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "listening_completions"