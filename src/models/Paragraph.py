from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Link
from pydantic import Field


class WordType(str, Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"


class WordModel(Document):
    word: str = Field(..., min_length=1)
    word_type: WordType = Field(default=WordType.NOUN)
    meaning: Optional[str] = None 

    class Settings:
        name = "words"


class ParagraphModel(Document):
    topic: str = Field(..., min_length=3) 
    content: str = Field(..., min_length=10) 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "paragraphs"



class SentenceModel(Document):
    sentence_text: str = Field(..., min_length=1)
    meaning: str = Field(..., min_length=1) 
    
    paragraph_id: Link[ParagraphModel]

    words: list[Link[WordModel]] = Field(default_factory=list)

    class Settings:
        name = "sentences"