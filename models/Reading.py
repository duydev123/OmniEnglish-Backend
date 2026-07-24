
from datetime import datetime
from time import timezone
from typing import Dict, List
from beanie import Document
from pydantic import Field

class ReadingVocabMatchingModel(Document):
    passage_id: str = Field(..., min_length=1)
    order: int = Field(default=1)
    

    pairs: List[Dict[str, str]] = Field(..., min_items=1)
    
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    class Settings:
        name = "reading_vocab_matchings"



class ReadingSentenceCompletionModel(Document):
    passage_id: str = Field(..., min_length=1)
    order: int = Field(default=2)
    

    template_text: str = Field(..., min_length=1)

    correct_answers: Dict[str, str] = Field(...)
    case_sensitive: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.UTC)

    class Settings:
        name = "reading_sentence_completions"


class ReadingMultipleChoiceModel(Document):
    passage_id: str = Field(..., min_length=1)
    order: int = Field(default=3)


    question_text: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=2)
    correct_answer: str = Field(..., min_length=1)
    
    created_at: datetime = Field(default_factory=datetime.UTC)

    class Settings:
        name = "reading_multiple_choices"