from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List

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
    ipa: Optional[str] = None               
    example_sentence: Optional[str] = None     
    image_url: Optional[str] = None
    class Settings:
        name = "words"


