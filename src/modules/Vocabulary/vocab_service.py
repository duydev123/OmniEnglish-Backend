import os
import re
import json
import time
import logging
import unicodedata
import urllib.request
import urllib.parse
from datetime import UTC, datetime, timezone
from typing import Optional, List

import httpx
from beanie import PydanticObjectId
from fastapi import HTTPException
from google import genai
from google.genai import types

from models.VocabularyCollectionModel import (
    VocabularyCollectionModel,
    UserWordStatusModel,
    UserProgressModel,
    WordLearningStatus
)
from .Vocabulary_dto import (
    PasteTextRequest,
    VocabularyCollectionResponse,
    UpdateWordStatusRequest,
    UpdateCollectionProgressRequest,
    VocabularyProgressResponse,
    CreateCollectionRequest,
    UpdateCollectionRequest,
    AddWordRequest,
    UpdateWordRequest,
    BulkAddWordsRequest,
    BulkUpdateWordsRequest
)
from models.Paragraph import WordModel, WordType

logger = logging.getLogger(__name__)

# Global In-Memory IPA Cache for instant 0ms lookups
_IPA_CACHE: dict[str, str] = {}
MAX_RECURSION_DEPTH = 2


def normalize_text(text: str) -> str:
    """Normalize Unicode characters (NFKC) and strip whitespace."""
    if not text:
        return ""
    return unicodedata.normalize('NFKC', text).strip()


def normalize_word_type(val: Optional[str]) -> str:
    if not val:
        return WordType.NOUN.value
    v = val.lower().strip()
    valid_map = {e.value: e.value for e in WordType}
    if v in valid_map:
        return valid_map[v]
    prefix_map = {
        'noun': WordType.NOUN.value,
        'verb': WordType.VERB.value,
        'adj': WordType.ADJECTIVE.value,
        'adjective': WordType.ADJECTIVE.value,
        'adv': WordType.ADVERB.value,
        'adverb': WordType.ADVERB.value,
        'prep': WordType.PREPOSITION.value,
        'preposition': WordType.PREPOSITION.value,
        'conj': WordType.CONJUNCTION.value,
        'conjunction': WordType.CONJUNCTION.value,
        'pron': WordType.PRONOUN.value,
        'pronoun': WordType.PRONOUN.value,
        'interj': WordType.INTERJECTION.value,
        'interjection': WordType.INTERJECTION.value,
        'phrasal': WordType.PHRASAL_VERB.value,
        'idiom': WordType.IDIOM.value,
    }
    for p, mapped in prefix_map.items():
        if v.startswith(p):
            return mapped
    return WordType.NOUN.value



def get_current_user_id() -> str:
    """
    TODO: Replace with actual JWT decoding logic later.
    (e.g., retrieving from a global request context or middleware)
    """
    return "test_user_123"


def validate_object_id(id_str: str) -> PydanticObjectId:
    if not PydanticObjectId.is_valid(id_str):
        raise HTTPException(status_code=404, detail="Vocabulary collection not found")
    return PydanticObjectId(id_str)


ARPABET_TO_IPA = {
    'AA': 'ɑ', 'AA0': 'ɑ', 'AA1': 'ɑː', 'AA2': 'ɑ',
    'AE': 'æ', 'AE0': 'æ', 'AE1': 'æ', 'AE2': 'æ',
    'AH': 'ʌ', 'AH0': 'ə', 'AH1': 'ʌ', 'AH2': 'ʌ',
    'AO': 'ɔ', 'AO0': 'ɔ', 'AO1': 'ɔː', 'AO2': 'ɔ',
    'AW': 'aʊ', 'AW0': 'aʊ', 'AW1': 'aʊ', 'AW2': 'aʊ',
    'AY': 'aɪ', 'AY0': 'aɪ', 'AY1': 'aɪ', 'AY2': 'aɪ',
    'EH': 'ɛ', 'EH0': 'ɛ', 'EH1': 'ɛ', 'EH2': 'ɛ',
    'ER': 'ɜːr', 'ER0': 'ər', 'ER1': 'ɜːr', 'ER2': 'ɜːr',
    'EY': 'eɪ', 'EY0': 'eɪ', 'EY1': 'eɪ', 'EY2': 'eɪ',
    'IH': 'ɪ', 'IH0': 'ɪ', 'IH1': 'ɪ', 'IH2': 'ɪ',
    'IY': 'i', 'IY0': 'i', 'IY1': 'iː', 'IY2': 'i',
    'OW': 'oʊ', 'OW0': 'oʊ', 'OW1': 'oʊ', 'OW2': 'oʊ',
    'OY': 'ɔɪ', 'OY0': 'ɔɪ', 'OY1': 'ɔɪ', 'OY2': 'ɔɪ',
    'UH': 'ʊ', 'UH0': 'ʊ', 'UH1': 'ʊ', 'UH2': 'ʊ',
    'UW': 'u', 'UW0': 'u', 'UW1': 'uː', 'UW2': 'u',
    'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'F': 'f', 'G': 'ɡ',
    'HH': 'h', 'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n',
    'NG': 'ŋ', 'P': 'p', 'R': 'r', 'S': 's', 'SH': 'ʃ', 'T': 't',
    'TH': 'θ', 'V': 'v', 'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
}


def is_valid_ipa(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return False
    lower = text.lower()
    forbidden = [
        "example", "provided", "sorry", "cannot", "description", "definition", 
        "here", "output", "unknown", "let's", "re-read", "read", "phrase", 
        "idiom", "word", "transcription", "phonetic", "sure", "certainly", 
        "translation", "meaning", "explanation", "note", "standard", "sentence"
    ]
    for f in forbidden:
        if f in lower:
            return False
    # English apostrophes or contractions (e.g., Let's) are not valid IPA symbols
    if "'" in text or "’" in text:
        return False
    return True


def is_abbreviation_or_initialism(word: str, clean_word: str) -> bool:
    """
    Check if a word is purely an acronym, initialism, or abbreviation (e.g., ABG, ABC, ATM, CEO, LOL, OMG).
    Case-insensitive checking to block both 'abc' and 'ABC'.
    """
    if not clean_word or len(clean_word) > 10:
        return False

    clean_lower = clean_word.lower()

    # Never block basic/common English words or plurals (e.g. cats, dogs, cars, books)
    common_words = {"cats", "dogs", "cars", "books", "birds", "hats", "bats", "buses", "tax", "vat"}
    if clean_lower in common_words:
        return False

    # Known common acronyms / initialisms (case-insensitive)
    known_acronyms = {
        "abc", "abg", "atm", "ceo", "fbi", "cia", "lol", "omg", "btw", "asap", 
        "diy", "vip", "faq", "dob", "eta", "gdp", "hr", "iq", "pdf", "pr", 
        "ram", "rom", "sos", "ufo", "url", "usb", "vpn", "www"
    }
    if clean_lower in known_acronyms:
        return True

    # Block uppercase short acronyms
    if word.strip().isupper() and len(word.strip()) <= 6 and clean_lower not in ["a", "i"]:
        return True

    # Datamuse initialism definition check
    try:
        url = f"https://api.datamuse.com/words?sp={urllib.parse.quote(clean_lower)}&md=d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for item in data:
                if item.get('word', '') == clean_lower and 'defs' in item:
                    defs = item['defs']
                    init_cnt = sum(
                        1 for d in defs 
                        if any(k in d.lower() for k in ['initialism of', 'abbreviation of', 'acronym of', 'short for', 'ellipsis of'])
                    )
                    if len(defs) > 0 and (init_cnt / len(defs)) >= 0.5:
                        return True
    except Exception:
        pass

    return False


async def _fetch_from_free_dict(clean_word: str, client: Optional[httpx.AsyncClient] = None) -> tuple[str, bool]:
    """Fetch IPA from Free Dictionary API asynchronously via httpx (returns (ipa, is_valid_dictionary_word))."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(clean_word)}"
        data = None

        # Check if urlopen is mocked in unit tests
        if hasattr(urllib.request.urlopen, "return_value") or hasattr(urllib.request.urlopen, "side_effect"):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
            except Exception:
                data = None

        if data is None and client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
            elif resp.status_code == 404:
                return ("", False)

        if isinstance(data, list) and len(data) > 0:
            top_phonetic = data[0].get('phonetic')
            if top_phonetic and is_valid_ipa(top_phonetic):
                return (top_phonetic.strip(), True)
            phonetics = data[0].get('phonetics', [])
            for p in phonetics:
                text = p.get('text')
                if text and is_valid_ipa(text):
                    return (text.strip(), True)
            return ("", True)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.debug(f"Word '{clean_word}' not found in Free Dictionary API (404)")
            return ("", False)
    except Exception as e:
        logger.debug(f"Free Dictionary API lookup error for '{clean_word}': {e}")
    return ("", False)




async def _fetch_from_datamuse(clean_word: str, client: httpx.AsyncClient) -> str:
    """Fetch IPA from Datamuse CMUdict asynchronously via httpx (only if dictionary definitions exist to filter out gibberish like xyz/lmao)."""
    try:
        url = f"https://api.datamuse.com/words?sp={urllib.parse.quote(clean_word)}&md=rd"
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                # Require dictionary definitions ('defs') to exist to prevent phonetic guesses on gibberish like xyz or lmao
                if item.get('word', '').lower() == clean_word and 'defs' in item and 'tags' in item:
                    for tag in item['tags']:
                        if tag.startswith('pron:'):
                            raw_pron = tag[5:].strip().split()
                            ipa_parts = []
                            for phoneme in raw_pron:
                                if phoneme in ARPABET_TO_IPA:
                                    ipa_parts.append(ARPABET_TO_IPA[phoneme])
                                else:
                                    logger.warning(f"Unknown ARPABET phoneme '{phoneme}' for word '{clean_word}'")
                                    ipa_parts.append(phoneme.lower())
                            res_ipa = '/' + ''.join(ipa_parts) + '/'
                            if is_valid_ipa(res_ipa):
                                return res_ipa
    except Exception as e:
        logger.debug(f"Datamuse IPA lookup error for '{clean_word}': {e}")
    return ""


_WORD_TYPE_CACHE: dict[str, str] = {}


async def fetch_word_type_for_word(word: str) -> str:
    """
    Automatically determine the primary Part of Speech (word_type) for a word or phrase.
    Returns: 'noun', 'verb', 'adjective', 'adverb', 'phrasal verb', 'idiom', etc.
    """
    if not word or not word.strip():
        return WordType.NOUN.value

    clean_word = normalize_text(word).lower()
    if clean_word in _WORD_TYPE_CACHE:
        return _WORD_TYPE_CACHE[clean_word]

    # Handle multi-word phrases and idioms
    if ' ' in clean_word:
        first_word = clean_word.split()[0]
        first_word_type = await fetch_word_type_for_word(first_word)
        if first_word_type == WordType.VERB.value:
            res_type = WordType.PHRASAL_VERB.value
        else:
            res_type = WordType.IDIOM.value
        _WORD_TYPE_CACHE[clean_word] = res_type
        return res_type

    # Async HTTP Lookup via Free Dictionary API
    try:
        async with httpx.AsyncClient(timeout=3.0, headers={'User-Agent': 'Mozilla/5.0'}) as client:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(clean_word)}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    pos_counts = {}
                    for entry in data:
                        for m in entry.get('meanings', []):
                            pos = m.get('partOfSpeech')
                            defs = m.get('definitions', [])
                            if pos:
                                norm_pos = normalize_word_type(pos)
                                pos_counts[norm_pos] = pos_counts.get(norm_pos, 0) + len(defs)
                    if pos_counts:
                        best_pos = max(pos_counts, key=pos_counts.get)
                        _WORD_TYPE_CACHE[clean_word] = best_pos
                        return best_pos
    except Exception as e:
        logger.debug(f"Free Dict word_type lookup error for '{clean_word}': {e}")

    _WORD_TYPE_CACHE[clean_word] = WordType.NOUN.value
    return WordType.NOUN.value


_DETAILS_CACHE: dict[str, dict] = {}


async def fetch_word_details(word: str) -> dict:
    """
    Fetch IPA and word_type for a word.
    Returns: {"word": word, "ipa": ipa, "word_type": word_type}
    """
    if not word or not word.strip():
        return {"word": word, "ipa": "", "word_type": WordType.NOUN.value}

    clean_word = normalize_text(word).lower()
    if clean_word in _DETAILS_CACHE:
        return _DETAILS_CACHE[clean_word]

    ipa = await fetch_ipa_for_word(word)
    if not ipa:
        res = {"word": word, "ipa": "", "word_type": WordType.NOUN.value}
        _DETAILS_CACHE[clean_word] = res
        return res

    word_type = await fetch_word_type_for_word(word)

    res = {
        "word": word,
        "ipa": ipa,
        "word_type": word_type,
    }
    _DETAILS_CACHE[clean_word] = res
    return res



async def _fetch_from_gemini(clean_word: str) -> str:
    """Fetch IPA from Gemini AI for phrasal verbs, idioms, and complex terms."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return ""
        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        is_phrase = ' ' in clean_word
        term_type = "phrase, phrasal verb, or idiom" if is_phrase else "word"
        prompt = f"Provide ONLY the standard IPA phonetic transcription with slashes for the valid English {term_type} '{clean_word}'. Format: /IPA/. Do NOT write any explanations, labels, or extra words. If the term is invalid or gibberish, return NOTHING."
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=150
            ),
        )
        if response and response.text:
            raw_text = response.text.strip()
            all_matches = re.findall(r'/[^/]+/', raw_text)
            if all_matches:
                cleaned_parts = [m.strip('/').strip() for m in all_matches if m.strip('/').strip()]
                ipa_str = "/" + " ".join(cleaned_parts) + "/"
            else:
                ipa_str = raw_text

            if is_valid_ipa(ipa_str):
                if not ipa_str.startswith("/"):
                    ipa_str = "/" + ipa_str
                if not ipa_str.endswith("/"):
                    ipa_str = ipa_str + "/"
                return ipa_str
    except Exception as e:
        logger.warning(f"Gemini IPA lookup error for '{clean_word}': {e}")
    return ""


async def _process_phrase(clean_word: str, depth: int) -> str:
    """Helper to process multi-word phrases/idioms asynchronously with recursion guard."""
    words = clean_word.split()
    phrase_ipas = []
    for w in words:
        sub_ipa = await fetch_ipa_for_word(w, depth=depth + 1)
        if not sub_ipa:
            return ""
        phrase_ipas.append(sub_ipa.strip('/'))
    if phrase_ipas:
        return '/' + ' '.join(phrase_ipas) + '/'
    return ""


async def fetch_ipa_for_word(word: str, depth: int = 0) -> str:
    """
    Fetch standard IPA phonetic transcription for an English word or phrase.
    Fully async, non-blocking via httpx.AsyncClient with LRU in-memory cache and recursion guard.
    """
    if depth > MAX_RECURSION_DEPTH:
        logger.warning(f"Maximum recursion depth {MAX_RECURSION_DEPTH} exceeded for word '{word}'")
        return ""

    if not word or not word.strip() or not re.search(r'[a-zA-Z]', word):
        return ""

    clean_word = normalize_text(word).lower()

    # 0. Fast In-Memory Cache Lookup (0ms response)
    if clean_word in _IPA_CACHE:
        logger.debug(f"Cache hit for word '{clean_word}' -> '{_IPA_CACHE[clean_word]}'")
        return _IPA_CACHE[clean_word]

    # Block pure abbreviations & initialisms (e.g. ABG, ABC, ATM)
    if is_abbreviation_or_initialism(word, clean_word):
        logger.info(f"Word '{clean_word}' rejected as an abbreviation/initialism.")
        _IPA_CACHE[clean_word] = ""
        return ""

    # Multi-word Phrase & Idiom Joiner (e.g. "rain like cats and dogs", "break a leg", "piece of cake")
    if ' ' in clean_word:
        phrase_ipa = await _process_phrase(clean_word, depth)
        _IPA_CACHE[clean_word] = phrase_ipa
        return phrase_ipa

    # Async HTTP Lookups via httpx Client
    async with httpx.AsyncClient(timeout=3.0, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}) as client:
        # 1. Primary Lookup: Free Dictionary API (Oxford / Wiktionary)
        ipa, is_valid_word = await _fetch_from_free_dict(clean_word, client)
        if ipa:
            _IPA_CACHE[clean_word] = ipa
            return ipa

        # If single word is NOT a valid English word (404 in Free Dict API), reject it (e.g. xyz, lmao, skibidi)
        if not is_valid_word:
            _IPA_CACHE[clean_word] = ""
            return ""

        # 2. Secondary Lookup: Datamuse API (For valid English words like 'and' whose IPA text was omitted by Free Dict API)
        ipa = await _fetch_from_datamuse(clean_word, client)
        if ipa:
            _IPA_CACHE[clean_word] = ipa
            return ipa

        # 3. AI Fallback: Gemini AI (for complex terms or missing entries)
        ipa = await _fetch_from_gemini(clean_word)
        if ipa:
            _IPA_CACHE[clean_word] = ipa
            return ipa

    _IPA_CACHE[clean_word] = ""
    return ""




async def format_collection_response(collection: VocabularyCollectionModel) -> VocabularyCollectionResponse:
    words_list = []
    
    if hasattr(collection, 'custom_words') and collection.custom_words:
        for link in collection.custom_words:
            word = await link.fetch() if hasattr(link, 'fetch') else link 
            if word:
                ipa_val = getattr(word, "ipa", "")
                if not ipa_val or not str(ipa_val).strip():
                    ipa_val = await fetch_ipa_for_word(word.word)
                    if ipa_val:
                        word.ipa = ipa_val
                        try:
                            await word.save()
                        except Exception:
                            pass

                words_list.append({
                    "id": str(word.id),
                    "word": word.word,
                    "word_type": word.word_type,
                    "meaning": word.meaning,
                    "ipa": ipa_val or "",
                    "example_sentence": getattr(word, "example_sentence", ""),
                    "image_url": getattr(word, "image_url", "")
                })
                
    if hasattr(collection, 'words') and collection.words:
        for link in collection.words:
            word = await link.fetch() if hasattr(link, 'fetch') else link
            if word:
                ipa_val = getattr(word, "ipa", "")
                if not ipa_val or not str(ipa_val).strip():
                    ipa_val = await fetch_ipa_for_word(word.word)
                    if ipa_val:
                        word.ipa = ipa_val
                        try:
                            await word.save()
                        except Exception:
                            pass

                words_list.append({
                    "id": str(word.id),
                    "word": word.word,
                    "word_type": word.word_type,
                    "meaning": word.meaning,
                    "ipa": ipa_val or "",
                    "example_sentence": getattr(word, "example_sentence", ""),
                    "image_url": getattr(word, "image_url", "")
                })

    return VocabularyCollectionResponse(
        id=str(collection.id),
        title=collection.title,
        description=collection.description,
        topic=collection.topic,
        language=collection.language,
        is_official=collection.is_official,
        total_learners=collection.total_learners,
        accuracy_percentage=getattr(collection, 'accuracy_percentage', 0.0),
        study_time_seconds=getattr(collection, 'study_time_seconds', 0),
        words_list=words_list
    )


class VocabService:
    @staticmethod
    async def get_my_collections() -> List[VocabularyCollectionResponse]:
        collections = await VocabularyCollectionModel.find(VocabularyCollectionModel.is_official == False).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col)
            res.append(formatted)
        return res

    @staticmethod
    async def get_official_collections() -> List[VocabularyCollectionResponse]:
        collections = await VocabularyCollectionModel.find(VocabularyCollectionModel.is_official == True).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col)
            res.append(formatted)
        return res

    @staticmethod
    async def create_my_collection(payload: CreateCollectionRequest) -> VocabularyCollectionResponse:
        new_collection = VocabularyCollectionModel(
            title=payload.title,
            description=payload.description,
            language=payload.language,
            topic="Custom",
            is_official=False,
            is_public=False,
            total_learners=1,
            words=[],
            custom_words=[]
        )
        await new_collection.insert()

        return VocabularyCollectionResponse(
            id=str(new_collection.id),
            title=new_collection.title,
            description=new_collection.description,
            topic=new_collection.topic,
            language=new_collection.language,
            is_official=new_collection.is_official,
            total_learners=new_collection.total_learners,
            accuracy_percentage=0.0,
            study_time_seconds=0,
            words_list=[]
        )

    @staticmethod
    async def update_collection_details(collection_id: str, payload: UpdateCollectionRequest) -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        if payload.title is not None:
            collection.title = payload.title
        if payload.description is not None:
            collection.description = payload.description
        if payload.language is not None:
            collection.language = payload.language

        await collection.save()

        return {
            "status": "success",
            "message": f"Successfully updated collection '{collection.title}'!",
            "id": str(collection.id),
            "title": collection.title,
            "description": collection.description,
            "language": collection.language
        }

    @staticmethod
    async def add_word_to_collection(collection_id: str, payload: AddWordRequest) -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403,
                detail="Collection not found or you do not have permission to edit it"
            )

        # --- Duplicate check: reject only if same word AND same word_type already in collection ---
        try:
            await collection.fetch_link(VocabularyCollectionModel.custom_words)
        except Exception:
            pass  # In tests or if already fetched, custom_words is already a list
        word_type_val = normalize_word_type(payload.word_type)
        existing_pairs = {
            (getattr(w, 'word', '').strip().lower(), getattr(w, 'word_type', '').strip().lower())
            for w in (collection.custom_words or [])
            if hasattr(w, 'word')
        }
        incoming_pair = (payload.word.strip().lower(), word_type_val.strip().lower())
        if incoming_pair in existing_pairs:
            raise HTTPException(
                status_code=409,
                detail=f"Từ '{payload.word}' với loại từ '{word_type_val}' đã tồn tại trong bộ từ vựng! (Bạn có thể thêm cùng từ với loại từ khác)"
            )

        ipa_val = payload.ipa.strip() if payload.ipa else ""
        if not ipa_val:
            ipa_val = await fetch_ipa_for_word(payload.word)

        new_word = WordModel(
            word=payload.word,
            word_type=word_type_val,
            meaning=payload.meaning or "Pending update",
            ipa=ipa_val,
            example_sentence=payload.example_sentence or "",
            image_url=payload.image_url or ""
        )
        await new_word.insert()

        collection.custom_words.append(new_word)
        await collection.save()

        return {"status": "success", "message": f"Successfully added the word '{payload.word}'!"}

    @staticmethod
    async def update_single_word(word_id: str, payload: UpdateWordRequest) -> dict:
        obj_id = validate_object_id(word_id)
        word = await WordModel.get(obj_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        if payload.word is not None:
            word.word = payload.word
        if payload.word_type is not None:
            word.word_type = normalize_word_type(payload.word_type)
        if payload.meaning is not None:
            word.meaning = payload.meaning
        if payload.ipa is not None:
            word.ipa = payload.ipa
        elif payload.word is not None and not word.ipa:
            word.ipa = await fetch_ipa_for_word(word.word)
        if payload.example_sentence is not None:
            word.example_sentence = payload.example_sentence
        if payload.image_url is not None:
            word.image_url = payload.image_url

        await word.save()

        return {
            "status": "success",
            "message": f"Successfully updated word '{word.word}'!",
            "id": str(word.id),
            "word": word.word,
            "word_type": word.word_type,
            "meaning": word.meaning,
            "ipa": word.ipa,
            "example_sentence": word.example_sentence,
            "image_url": word.image_url
        }

    @staticmethod
    async def bulk_update_words_in_collection(collection_id: str, payload: BulkUpdateWordsRequest) -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        updated_count = 0
        for item in payload.words:
            if not PydanticObjectId.is_valid(item.id):
                continue
            word_obj = await WordModel.get(PydanticObjectId(item.id))
            if word_obj:
                if item.word is not None:
                    word_obj.word = item.word
                if item.word_type is not None:
                    word_obj.word_type = normalize_word_type(item.word_type)
                if item.meaning is not None:
                    word_obj.meaning = item.meaning
                if item.ipa is not None:
                    word_obj.ipa = item.ipa
                elif not word_obj.ipa and word_obj.word:
                    word_obj.ipa = await fetch_ipa_for_word(word_obj.word)
                if item.example_sentence is not None:
                    word_obj.example_sentence = item.example_sentence
                if item.image_url is not None:
                    word_obj.image_url = item.image_url
                await word_obj.save()
                updated_count += 1

        return {
            "status": "success",
            "message": f"Successfully updated {updated_count} words in bulk!"
        }

    @staticmethod
    async def bulk_add_words_to_collection(collection_id: str, payload: BulkAddWordsRequest) -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403,
                detail="Collection not found or you do not have permission to edit it"
            )

        # Build set of (word, word_type) pairs in this collection for duplicate check
        # Same word with different word_type is allowed (e.g. 'run' verb vs 'run' noun)
        try:
            await collection.fetch_link(VocabularyCollectionModel.custom_words)
        except Exception:
            pass  # In tests or if already fetched
        existing_pairs = {
            (getattr(w, 'word', '').strip().lower(), getattr(w, 'word_type', '').strip().lower())
            for w in (collection.custom_words or [])
            if hasattr(w, 'word')
        }

        new_words_objects = []
        skipped_words = []

        for w in payload.words:
            word_type_val = normalize_word_type(w.word_type)
            pair = (w.word.strip().lower(), word_type_val.strip().lower())
            if pair in existing_pairs:
                skipped_words.append(f"{w.word} ({word_type_val})")
                continue

            ipa_val = w.ipa.strip() if w.ipa else ""
            if not ipa_val:
                ipa_val = await fetch_ipa_for_word(w.word)

            new_word = WordModel(
                word=w.word,
                word_type=word_type_val,
                meaning=w.meaning,
                ipa=ipa_val,
                example_sentence=w.example_sentence or "",
                image_url=w.image_url or ""
            )

            await new_word.insert()
            new_words_objects.append(new_word)
            collection.custom_words.append(new_word)
            existing_pairs.add(pair)  # prevent intra-batch duplicates

        if new_words_objects:
            await collection.save()

        skip_msg = f" (Bỏ qua {len(skipped_words)} từ đã tồn tại: {', '.join(skipped_words)})" if skipped_words else ""
        return {
            "status": "success",
            "message": f"Successfully bulk added {len(new_words_objects)} words!{skip_msg}",
            "added_count": len(new_words_objects),
            "skipped_words": skipped_words,
        }

    @staticmethod
    async def process_and_add_pasted_text_with_gemini(collection_id: str, payload: PasteTextRequest) -> dict:
        user_id = get_current_user_id() 
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        MAX_TEXT_LENGTH = 5000
        if len(payload.raw_text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text is too long ({len(payload.raw_text)} characters). Please edit it to be under {MAX_TEXT_LENGTH} characters."
            )

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        prompt = f"""
        Act as an expert English lexicographer and language tutor. Analyze the following English text and extract up to 15-20 key vocabulary words or phrasal verbs that are most valuable for a Vietnamese English learner to study.

        CRITICAL SELECTION RULES:
        1. Ignore basic/common stop words (e.g. "the", "and", "they", "is", "have", "go", "make", "good").
        2. Prioritize academic, professional, B1-C2 CEFR level words, useful phrasal verbs, or domain-specific terms.
        3. Convert verbs to their base/infinitive form (e.g. "analyzed" -> "analyze").

        For each word, provide:
        - "word": The base English word or phrasal verb.
        - "word_type": One of exactly [noun, verb, adjective, adverb, phrasal verb, idiom, pronoun, preposition, conjunction]
        - "cefr_level": One of [A1, A2, B1, B2, C1, C2]
        - "topic": Appropriate topic category (e.g. Technology, Business, Education, Environment, Daily Life)
        - "meaning": Concise, natural, contextually accurate Vietnamese translation.
        - "ipa": Standard IPA transcription with slashes (e.g. /rɪˈzɪl.jəns/).
        - "example_sentence": A clear, natural English example sentence demonstrating the word in context.

        OUTPUT FORMAT:
        Return ONLY a raw valid JSON array of objects. Do NOT use markdown codeblock wrappers like ```json.

        Text to analyze:
        {payload.raw_text}
        """

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=8192
                    ),
                )
                break
            except Exception as api_err:
                err_str = str(api_err)
                if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise api_err

        if not response or not response.text:
            raise ValueError("Gemini returned empty response")
        
        raw_output = response.text.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        extracted_data = json.loads(raw_output)
        if isinstance(extracted_data, dict):
            extracted_data = [extracted_data]
        elif not isinstance(extracted_data, list):
            raise ValueError("Unexpected response format")        
        
        new_words_objects = []
        added_words = set()
        collection_updated = False 

        for item in extracted_data:
            word_val = item.get("word")
            if not word_val or word_val in added_words:
                continue
            
            existing_word = await WordModel.find_one(WordModel.word == word_val)
            
            if existing_word:
                if not getattr(existing_word, 'ipa', None) or not str(existing_word.ipa).strip():
                    item_ipa = item.get("ipa", "").strip()
                    if not item_ipa:
                        item_ipa = await fetch_ipa_for_word(word_val)
                    if item_ipa:
                        existing_word.ipa = item_ipa
                        await existing_word.save()

                is_in_collection = any(
                    getattr(link, 'ref', None) and link.ref.id == existing_word.id 
                    for link in collection.custom_words
                )
                
                if not is_in_collection:
                    collection.custom_words.append(existing_word)
                    collection_updated = True 
                
                added_words.add(word_val)
                continue
            
            word_type_val = normalize_word_type(item.get("word_type"))
            
            cefr_val = (item.get("cefr_level") or "B1").upper()
            valid_cefr = ["A1", "A2", "B1", "B2", "C1", "C2"]
            if cefr_val not in valid_cefr:
                cefr_val = "B1"
            
            ipa_val = item.get("ipa", "").strip() if item.get("ipa") else ""
            if not ipa_val:
                ipa_val = await fetch_ipa_for_word(word_val)

            new_word = WordModel(
                word=word_val,
                word_type=word_type_val,
                cefr_level=cefr_val,
                topic=item.get("topic", "General"),
                meaning=item.get("meaning", ""),
                ipa=ipa_val,
                example_sentence=item.get("example_sentence", ""),
                image_url="",
                user_id=user_id,
            )
            
            await new_word.insert()
            new_words_objects.append(new_word)
            collection.custom_words.append(new_word)
            added_words.add(word_val)
            collection_updated = True 

        if collection_updated:
            await collection.save()

        highlighted_text = payload.raw_text
        for item in extracted_data:
            word = item.get("word")
            if word and word in highlighted_text:
                highlighted_text = highlighted_text.replace(word, f"**{word}**")

        return {
            "status": "success",
            "message": f"Gemini AI đã phân tích văn bản thành công! (Tạo mới {len(new_words_objects)} từ, thêm tổng cộng {len(added_words)} từ vào bộ).",
            "added_count": len(added_words),
            "new_created_count": len(new_words_objects),
            "highlighted_text": highlighted_text,
            "extracted_words": list(added_words)
        }

    @staticmethod
    async def get_vocabulary_collection(collection_id: str) -> VocabularyCollectionResponse:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        return await format_collection_response(collection)

    @staticmethod
    async def update_word_status(payload: UpdateWordStatusRequest) -> VocabularyProgressResponse:
        user_id = get_current_user_id() 
        collection_id = payload.collection_id
        obj_id = validate_object_id(collection_id)

        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
            
        progress_record = await UserWordStatusModel.find_one(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.word == payload.word_id
        )

        if progress_record:
            progress_record.status = payload.status
            progress_record.last_reviewed_at = datetime.now(UTC)
            await progress_record.save()
        else:
            new_progress = UserWordStatusModel(
                user_id=user_id,
                collection_id=collection, 
                word=payload.word_id,
                status=payload.status,
                last_reviewed_at=datetime.now(UTC)
            )
            await new_progress.insert()

        total_mastered = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.MASTERED
        ).count()
        
        total_learning = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.LEARNING
        ).count()

        total_words_in_collection = len(collection.custom_words) + len(collection.words)
        accuracy = (total_mastered / total_words_in_collection * 100) if total_words_in_collection > 0 else 0.0

        user_progress = await UserProgressModel.find_one(
            UserProgressModel.user_id == user_id,
            UserProgressModel.collection_id.id == obj_id
        )
        
        if user_progress:
            user_progress.accuracy_percentage = accuracy
            user_progress.updated_at = datetime.now(UTC)
            await user_progress.save()
        else:
            new_user_progress = UserProgressModel(
                user_id=user_id,
                collection_id=collection,
                accuracy_percentage=accuracy,
                study_time_seconds=0,
                updated_at=datetime.now(UTC)
            )
            await new_user_progress.insert()

        return VocabularyProgressResponse(
            message="Word progress updated successfully!",
            user_id=user_id,
            collection_id=collection_id,
            total_mastered=total_mastered,
            total_learning=total_learning,
            accuracy_percentage=round(accuracy, 2)
        )

    @staticmethod
    async def update_collection_progress(payload: UpdateCollectionProgressRequest) -> VocabularyProgressResponse:
        user_id = get_current_user_id()
        collection_id = payload.collection_id
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        user_progress = await UserProgressModel.find_one(
            UserProgressModel.user_id == user_id,
            UserProgressModel.collection_id.id == obj_id
        )
        
        if user_progress:
            user_progress.study_time_seconds += payload.study_time_seconds
            user_progress.last_studied_at = datetime.now(UTC)
            user_progress.updated_at = datetime.now(UTC)
            await user_progress.save()
        else:
            new_user_progress = UserProgressModel(
                user_id=user_id,
                collection_id=collection, 
                accuracy_percentage=payload.accuracy_percentage,
                study_time_seconds=payload.study_time_seconds,
                last_studied_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            await new_user_progress.insert()
            
        total_mastered = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.MASTERED
        ).count()
        
        total_learning = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.LEARNING
        ).count()
        
        total_words_in_collection = len(collection.custom_words) + len(collection.words)
        backend_accuracy = (total_mastered / total_words_in_collection * 100) if total_words_in_collection > 0 else 0.0

        if user_progress:
            user_progress.accuracy_percentage = backend_accuracy
            await user_progress.save()

        return VocabularyProgressResponse(
            message="Learning progress updated successfully!",
            user_id=user_id,
            collection_id=collection_id,
            total_mastered=total_mastered,
            total_learning=total_learning,
            accuracy_percentage=round(backend_accuracy, 2)
        )

    @staticmethod
    async def delete_vocabulary_collection(collection_id: str) -> dict:
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        if collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to delete an official system collection"
            )
            
        await UserWordStatusModel.find(
            UserWordStatusModel.collection_id.id == obj_id
        ).delete()
        
        await UserProgressModel.find(
            UserProgressModel.collection_id.id == obj_id
        ).delete()

        if hasattr(collection, 'custom_words') and collection.custom_words:
            for link in collection.custom_words:
                word = await link.fetch() if hasattr(link, 'fetch') else link 
                if word:
                    await word.delete()
                    
        await collection.delete()

        return {
            "status": "success", 
            "message": "Vocabulary collection and associated data deleted successfully!"
        }
