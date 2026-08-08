import re
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List

from beanie import Document, Link
from pydantic import Field, field_validator


class WordType(str, Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PHRASAL_VERB = "phrasal verb"
    IDIOM = "idiom"
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
    cefr_level: Optional[str] = None
    topic: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("word_type", mode="before")
    @classmethod
    def validate_word_type(cls, v):
        if not v:
            return WordType.NOUN
        if isinstance(v, WordType):
            return v
        v_str = str(v).lower().strip()
        valid_vals = [e.value for e in WordType]
        if v_str in valid_vals:
            return WordType(v_str)
        parts = re.split(r"[/,;\s]+", v_str)
        for p in parts:
            p = p.strip()
            if p in valid_vals:
                return WordType(p)
            if p.startswith("noun"): return WordType.NOUN
            if p.startswith("verb"): return WordType.VERB
            if p.startswith("adj"): return WordType.ADJECTIVE
            if p.startswith("adv"): return WordType.ADVERB
            if p.startswith("phrasal"): return WordType.PHRASAL_VERB
            if p.startswith("idiom"): return WordType.IDIOM
            if p.startswith("pron"): return WordType.PRONOUN
            if p.startswith("prep"): return WordType.PREPOSITION
            if p.startswith("conj"): return WordType.CONJUNCTION
            if p.startswith("interj"): return WordType.INTERJECTION
        return WordType.NOUN

    class Settings:
        name = "words"


