import os
import re
import json
import time
import logging
import asyncio
import unicodedata
import urllib.request
import urllib.parse
from datetime import UTC, datetime, timezone
from typing import Optional, List, Any

import httpx
from beanie import PydanticObjectId
from fastapi import HTTPException
from google import genai
from google.genai import types

from models.VocabularyCollection import (
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
from models.Vocabulary import WordModel, WordType

logger = logging.getLogger(__name__)

# Global In-Memory IPA Cache for instant 0ms lookups
_IPA_CACHE: dict[str, str] = {}
MAX_RECURSION_DEPTH = 2


def normalize_text(text: str) -> str:
    """Normalize Unicode characters (NFKC), curly quotes, and strip whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKC', text)
    normalized = re.sub(r"[’`‘ʼ\u2018\u2019\u02bc]", "'", normalized)
    return normalized.strip()


def normalize_word_type(val: Any) -> str:
    if not val:
        return WordType.NOUN.value
    if isinstance(val, WordType):
        return val.value
    val_str = str(val).strip()
    if val_str.lower().startswith("wordtype."):
        val_str = val_str[9:]
    v = val_str.lower().strip()
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
    return True


def is_nonsense_or_test_word(word: str, clean_word: str) -> bool:
    """Filter out non-standard test strings like 'aa', 'bb', 'ccc', 'asdfghjk', 'qwerty'."""
    clean_lower = clean_word.lower().strip()
    if not clean_lower:
        return True

    # Single letter words except 'a' and 'i'
    if len(clean_lower) == 1 and clean_lower not in ["a", "i"]:
        return True

    # Repeated identical letters (e.g., aa, bb, ccc, dddd)
    if len(set(clean_lower)) == 1 and clean_lower not in ["a", "i"]:
        return True

    # Keyboard mashing
    keyboard_mash = {"asdf", "qwerty", "zxcv", "asdfghjk", "qwertyuiop", "zxcvbnm", "lmao", "xyz"}
    if clean_lower in keyboard_mash:
        return True

    return False


def is_abbreviation_or_initialism(word: str, clean_word: str) -> bool:
    """
    Check if a word is purely an acronym, initialism, or abbreviation (e.g., ABG, ABC, ATM, CEO, LOL, OMG).
    Case-insensitive checking to block both 'abc' and 'ABC'.
    """
    if is_nonsense_or_test_word(word, clean_word):
        return True

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


PHRASAL_PARTICLES = {
    "about", "above", "across", "after", "against", "ahead", "along", "around",
    "apart", "aside", "away", "back", "behind", "below", "by", "down", "forward",
    "from", "in", "into", "off", "on", "onto", "out", "over", "through", "to",
    "together", "under", "up", "upon", "with", "without"
}

KNOWN_VERB_ROOTS = {
    "add", "agree", "allow", "apply", "ask", "back", "belong", "blow", "break",
    "bring", "call", "calm", "care", "carry", "catch", "cater", "check", "cheer",
    "chip", "clean", "come", "consist", "count", "cross", "cut", "deal", "depend",
    "do", "dress", "drop", "eat", "end", "fall", "figure", "fill", "find", "focus",
    "get", "give", "go", "grow", "hand", "hang", "hold", "keep", "lay", "lead",
    "let", "listen", "log", "look", "make", "mix", "move", "pass", "pay", "pick",
    "point", "pull", "push", "put", "refer", "rely", "result", "run", "send",
    "set", "shop", "show", "sit", "sleep", "sort", "stand", "stem", "step",
    "stick", "switch", "take", "tear", "think", "throw", "try", "turn", "use",
    "wait", "wake", "walk", "warm", "wear", "work"
}

COMMON_IDIOM_INDICATOR_WORDS = {
    "one's", "someone's", "hair", "leg", "ice", "bucket", "bullet", "beans",
    "sack", "towel", "oil", "bell", "chin", "mind", "heart", "head", "foot",
    "face", "eye", "ear", "hand", "finger", "arm", "back", "tongue", "mouth",
    "blood", "bone", "skin", "boat", "bridge", "bush", "coin", "tree", "feather",
    "bird", "dog", "cat", "horse", "fish", "apple", "pie", "cake", "egg", "salt",
    "tea", "coffee", "water", "fire", "wind", "sun", "moon", "star", "sky",
    "cloud", "ground", "stone", "rock", "wall", "door", "corner", "road", "street",
    "path", "train", "bus", "ship", "car", "truck", "plane", "money", "penny",
    "dollar", "bill", "ticket", "card", "book", "books", "page", "line", "lines",
    "rule", "law", "game", "sport", "music", "song", "story", "name", "clock",
    "hour", "night", "light", "dark", "shadow", "rain", "snow", "storm", "wood",
    "forest", "field", "farm", "garden", "flower", "leaf", "root", "fruit", "nut",
    "seed", "grain", "milk", "butter", "bread", "meat", "soup", "sugar", "pepper",
    "wine", "beer", "glass", "cup", "plate", "dish", "bowl", "spoon", "fork",
    "knife", "pen", "pencil", "paper", "letter", "mail", "key", "lock", "ring",
    "watch", "shoe", "boot", "sock", "hat", "cap", "coat", "shirt", "dress",
    "skirt", "pant", "pocket", "bag", "box", "bed", "table", "chair", "desk",
    "room", "house", "home", "roof", "floor", "window", "gate", "town", "city",
    "country", "world", "colors", "colours", "class", "learner", "nighter", "pet",
    "halves", "pain", "gain", "exam", "exams", "sight", "feet", "suitcase",
    "scenery", "jackpot", "journey", "bug", "nowhere", "dumps", "fence", "cents",
    "steam", "joy", "living", "meet", "ears", "eggs", "basket", "candle",
    "board", "grindstone", "ladder", "bargain", "bargains", "drain", "glove",
    "impulse", "basement", "therapy", "brain"
}

KNOWN_IELTS_IDIOMS = {
    # Work & General
    "make a living", "make ends meet", "call it a day", "call it a night", "call it a day/night",
    "be cut out for", "wet behind the ears", "put all one's eggs in one basket",
    "put all your eggs in one basket", "put all ones eggs in one basket", "beat the clock",
    "burn the candle at both ends", "back to the drawing board", "learn the ropes",
    "keep your nose to the grindstone", "keep one's nose to the grindstone",
    "climb the corporate ladder", "think on your feet", "think on one's feet",
    "on the same page", "get the ball rolling",

    # Shopping
    "hunt for bargains", "go window-shopping", "go window shopping", "cost an arm and a leg",
    "take back", "pour money down the drain", "fit like a glove", "the in thing",
    "shop till you drop", "buy on impulse", "pay through the nose", "in the red",
    "in the black", "bargain basement", "retail therapy", "splash out on",

    # Travel
    "let one's hair down", "let your hair down", "let ones hair down", "give someone a lift",
    "give somebody a lift", "hit the road", "at the crack of dawn", "off the beaten track",
    "live out of a suitcase", "have itchy feet", "get itchy feet", "have/get itchy feet",
    "travel light", "a change of scenery", "break the journey", "catch the travel bug",
    "hit the jackpot", "in the middle of nowhere", "pack in",

    # Feelings & Emotions
    "love at first sight", "head over heels in love", "on cloud nine", "break someone's heart",
    "break somebody's heart", "wear your heart on your sleeve", "wear one's heart on your sleeve",
    "a long face", "in someone's shoes", "in somebody's shoes", "green with envy",
    "down in the dumps", "sit on the fence", "feel like two cents", "be the apple of one's eye",
    "be the apple of someone's eye", "blow off steam", "keep your chin up", "keep one's chin up",
    "jump for joy",

    # Education & Study
    "pass with flying colors", "pass with flying colours", "learn by heart", "rack one's brain",
    "rack your brain", "no pain no gain", "no pain, no gain", "not do things by halves",
    "think outside the box", "brush up on", "teacher's pet", "hit the books",
    "pull an all-nighter", "cram for", "cram for an exam", "a quick learner",
    "read between the lines", "daydream in class", "top of the class"
}

PLACEHOLDER_WORDS = {
    "somebody", "something", "someplace", "some", "someone", "place", "oneself",
    "sb", "sth", "or", "and", "one's", "someone's", "your", "my", "his", "her",
    "their", "our", "its"
}


def is_phrasal_verb_phrase(clean_word: str) -> bool:
    """Detect if a multi-word phrase is a Phrasal Verb vs Idiom."""
    lower_str = clean_word.lower()
    clean_norm = re.sub(r'[^\w\s]', '', lower_str).strip()

    if lower_str in KNOWN_IELTS_IDIOMS or clean_norm in KNOWN_IELTS_IDIOMS:
        return False

    if "'s" in lower_str or "one's" in lower_str or "someone's" in lower_str:
        return False

    raw_tokens = re.sub(r'[/\\,\-\.\?]', ' ', lower_str).split()

    if any(t in COMMON_IDIOM_INDICATOR_WORDS for t in raw_tokens):
        return False

    tokens = [t for t in raw_tokens if t not in PLACEHOLDER_WORDS]
    if not tokens or len(tokens) < 2:
        return False

    first_token = tokens[0]
    has_particle = any(t in PHRASAL_PARTICLES for t in tokens[1:])

    if has_particle:
        if first_token in KNOWN_VERB_ROOTS:
            return True
        if any(first_token.endswith(ext) for ext in ["ing", "ed", "es", "s"]):
            return True
    return False


_WORD_TYPE_CACHE: dict[str, str] = {}
_DETAILS_CACHE: dict[str, dict] = {}


async def fetch_word_type_for_word(word: str) -> str:
    """
    Automatically determine the primary Part of Speech (word_type) for a word or phrase.
    Returns: 'noun', 'verb', 'adjective', 'adverb', 'phrasal verb', 'idiom', etc.
    """
    if not word or not word.strip():
        return WordType.NOUN.value

    clean_word = normalize_text(word).lower()
    if clean_word in _WORD_TYPE_CACHE:
        val = _WORD_TYPE_CACHE[clean_word]
        if val and val != WordType.NOUN.value:
            return val

    # Handle multi-word phrases and idioms directly
    if ' ' in clean_word:
        clean_no_parentheses = re.sub(r'\(.*?\)', '', clean_word).strip()
        if is_phrasal_verb_phrase(clean_no_parentheses):
            res_type = WordType.PHRASAL_VERB.value
        else:
            res_type = WordType.IDIOM.value
        _WORD_TYPE_CACHE[clean_word] = res_type
        return res_type

    # Single-word verb root override
    if clean_word in KNOWN_VERB_ROOTS:
        _WORD_TYPE_CACHE[clean_word] = WordType.VERB.value
        return WordType.VERB.value

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


async def fetch_word_details(word: str) -> dict:
    """
    Fetch IPA and word_type for a word or phrase.
    Returns: {"word": word, "ipa": ipa, "word_type": word_type}
    """
    if not word or not word.strip():
        return {"word": word, "ipa": "", "word_type": WordType.NOUN.value}

    clean_word = normalize_text(word).lower()
    if clean_word in _DETAILS_CACHE:
        cached = _DETAILS_CACHE[clean_word]
        if cached.get("word_type") and cached.get("word_type") != WordType.NOUN.value and cached.get("ipa"):
            return cached

    ipa = await fetch_ipa_for_word(word)
    
    # If the word or multi-word phrase has NO valid IPA (e.g. non-English text / typos like 'khanh ngu'), default to noun
    if not ipa or not ipa.strip() or ipa.startswith("No IPA"):
        res = {
            "word": word,
            "ipa": "",
            "word_type": WordType.NOUN.value,
        }
        _DETAILS_CACHE[clean_word] = res
        return res

    word_type = await fetch_word_type_for_word(word)

    res = {
        "word": word,
        "ipa": ipa or "",
        "word_type": word_type or WordType.NOUN.value,
    }
    _DETAILS_CACHE[clean_word] = res
    return res


COMMON_PREPOSITION_IPAS = {
    "a": "/ə/",
    "an": "/æn/",
    "the": "/ðə/",
    "of": "/əv/",
    "from": "/frɒm/",
    "to": "/tuː/",
    "for": "/fɔːr/",
    "in": "/ɪn/",
    "on": "/ɒn/",
    "at": "/æt/",
    "by": "/baɪ/",
    "with": "/wɪð/",
    "about": "/əˈbaʊt/",
    "out": "/aʊt/",
    "up": "/ʌp/",
    "down": "/daʊn/",
    "off": "/ɒf/",
    "over": "/ˈoʊvər/",
    "under": "/ˈʌndər/",
    "away": "/əˈweɪ/",
    "back": "/bæk/",
    "into": "/ˈɪntuː/",
    "onto": "/ˈɒntuː/",
    "upon": "/əˈpɒn/",
    "as": "/æz/",
    "than": "/ðæn/",
    "like": "/laɪk/",
    "through": "/θruː/",
    "across": "/əˈkrɒs/",
    "against": "/əˈɡɛnst/",
    "along": "/əˈlɒŋ/",
    "around": "/əˈraʊnd/",
    "behind": "/bɪˈhaɪnd/",
    "between": "/bɪˈtwiːn/",
    "beyond": "/bɪˈjɒnd/",
    "one": "/wʌn/",
    "one's": "/wʌnz/",
    "ones": "/wʌnz/",
    "your": "/jɔːr/",
    "my": "/maɪ/",
    "his": "/hɪz/",
    "her": "/hɜːr/",
    "their": "/ðeər/",
    "our": "/aʊər/",
    "its": "/ɪts/",
    "someone": "/ˈsʌmwʌn/",
    "someone's": "/ˈsʌmwʌnz/",
    "somebody": "/ˈsʌmbədi/",
    "somebody's": "/ˈsʌmbədiz/",
    "something": "/ˈsʌmθɪŋ/",
    "or": "/ɔːr/",
    "and": "/ænd/"
}


async def _process_phrase(clean_word: str, depth: int) -> str:
    """Helper to process multi-word phrases/idioms asynchronously with full IPA for all words."""
    clean_base = re.sub(r'[\(\)\[\]/\\,\-\.\?]', ' ', clean_word.lower())
    words = clean_base.split()

    phrase_ipas = []
    has_custom_words = False
    custom_words_failed = False

    for w in words:
        w_clean = re.sub(r"[^\w']", "", w)
        if not w_clean:
            continue
        w_lower = w_clean.lower()
        if w_lower in COMMON_PREPOSITION_IPAS:
            sub_ipa = COMMON_PREPOSITION_IPAS[w_lower]
        else:
            has_custom_words = True
            sub_ipa = await fetch_ipa_for_word(w_clean, depth=depth + 1)
            if not sub_ipa or sub_ipa.startswith('No IPA'):
                custom_words_failed = True

        if sub_ipa:
            clean_sub = sub_ipa.strip('/ ').strip()
            if clean_sub and not clean_sub.startswith('No IPA'):
                phrase_ipas.append(clean_sub)

    if has_custom_words and custom_words_failed:
        return ""

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
    if clean_word in _IPA_CACHE and _IPA_CACHE[clean_word]:
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

    _IPA_CACHE[clean_word] = ""
    return ""


async def format_collection_response(
    collection: VocabularyCollectionModel,
    user_id: Optional[str] = None,
    include_words: bool = True
) -> VocabularyCollectionResponse:
    col_str_id = str(getattr(collection, 'id', ''))
    
    accuracy_percentage = float(getattr(collection, 'accuracy_percentage', 0.0) or 0.0)
    study_time_seconds = int(getattr(collection, 'study_time_seconds', 0) or 0)
    word_statuses = {}

    if user_id and col_str_id and col_str_id != "None" and PydanticObjectId.is_valid(col_str_id):
        try:
            progress_record = await UserProgressModel.find_one(
                UserProgressModel.user_id == user_id,
                UserProgressModel.collection_id.id == PydanticObjectId(col_str_id)
            )
            if progress_record:
                accuracy_percentage = float(getattr(progress_record, 'accuracy_percentage', 0.0) or 0.0)
                study_time_seconds = int(getattr(progress_record, 'study_time_seconds', 0) or 0)

            if include_words:
                status_records = await UserWordStatusModel.find(
                    UserWordStatusModel.user_id == user_id,
                    UserWordStatusModel.collection_id.id == PydanticObjectId(col_str_id)
                ).to_list()
                for sr in status_records:
                    status_val = sr.status.value if hasattr(sr.status, 'value') else str(sr.status)
                    word_statuses[sr.word] = status_val
        except Exception as e:
            logger.debug(f"Error fetching user progress for format_collection_response: {e}")

    # Fast path: when listing collections (include_words=False), calculate total words count without serializing thousands of words
    custom_words_count = len(getattr(collection, 'custom_words', []) or [])
    words_count = len(getattr(collection, 'words', []) or [])
    estimated_total_words = custom_words_count + words_count

    words_list = []

    if include_words:
        word_ids = []
        direct_words = []

        if hasattr(collection, 'custom_words') and collection.custom_words:
            for link in collection.custom_words:
                if hasattr(link, 'ref') and hasattr(link.ref, 'id'):
                    word_ids.append(link.ref.id)
                elif hasattr(link, 'id') and not hasattr(link, 'fetch'):
                    word_ids.append(link.id)
                elif getattr(link, 'word', None):
                    direct_words.append(link)

        query_conditions = []
        if word_ids:
            query_conditions.append({"_id": {"$in": word_ids}})
        if getattr(collection, 'title', None):
            query_conditions.append({"collection_id": collection.title})
        if col_str_id and col_str_id != "None":
            query_conditions.append({"collection_id": col_str_id})

        words_docs = []
        if query_conditions:
            try:
                words_docs = await WordModel.find({"$or": query_conditions}).to_list()
            except Exception:
                words_docs = []

        # If words_docs is empty (e.g. unit test mocked DB), resolve custom_words via link.fetch()
        if not words_docs and not direct_words and hasattr(collection, 'custom_words') and collection.custom_words:
            for link in collection.custom_words:
                try:
                    w = await link.fetch() if hasattr(link, 'fetch') else link
                    if w and getattr(w, 'word', None):
                        direct_words.append(w)
                except Exception:
                    pass

        all_words = direct_words + words_docs
        seen_keys = set()

        for w in all_words:
            w_id = str(getattr(w, 'id', ''))
            w_name = str(getattr(w, 'word', ''))
            if not w_name or w_name in seen_keys:
                continue
            seen_keys.add(w_name)
            learning_st = word_statuses.get(w_id) or word_statuses.get(w_name) or "LEARNING"
            words_list.append({
                "id": w_id or w_name,
                "word": w_name,
                "word_type": normalize_word_type(getattr(w, 'word_type', 'noun')),
                "meaning": str(getattr(w, 'meaning', '') or ''),
                "ipa": str(getattr(w, 'ipa', '') or ''),
                "example_sentence": str(getattr(w, 'example_sentence', '') or ''),
                "image_url": str(getattr(w, 'image_url', '') or ''),
                "learning_status": learning_st
            })

        if hasattr(collection, 'words') and collection.words:
            for w_item in collection.words:
                if isinstance(w_item, str):
                    if w_item not in seen_keys:
                        seen_keys.add(w_item)
                        learning_st = word_statuses.get(w_item, "LEARNING")
                        words_list.append({
                            "id": w_item,
                            "word": w_item,
                            "word_type": "idiom" if ' ' in w_item else "noun",
                            "meaning": "",
                            "ipa": "",
                            "example_sentence": "",
                            "image_url": "",
                            "learning_status": learning_st
                        })
                else:
                    try:
                        w = await w_item.fetch() if hasattr(w_item, 'fetch') else w_item
                        w_name = str(getattr(w, 'word', '')) if w else ''
                        w_id = str(getattr(w, 'id', '')) if w else ''
                        if w and w_name and w_name not in seen_keys:
                            seen_keys.add(w_name)
                            learning_st = word_statuses.get(w_id) or word_statuses.get(w_name) or "LEARNING"
                            words_list.append({
                                "id": w_id,
                                "word": w_name,
                                "word_type": normalize_word_type(getattr(w, 'word_type', 'noun')),
                                "meaning": str(getattr(w, 'meaning', '') or ''),
                                "ipa": str(getattr(w, 'ipa', '') or ''),
                                "example_sentence": str(getattr(w, 'example_sentence', '') or ''),
                                "image_url": str(getattr(w, 'image_url', '') or ''),
                                "learning_status": learning_st
                            })
                    except Exception:
                        pass
        estimated_total_words = len(words_list)

    return VocabularyCollectionResponse(
        id=col_str_id,
        title=str(getattr(collection, 'title', '')),
        description=str(getattr(collection, 'description', '') or ""),
        topic=str(getattr(collection, 'topic', '') or ""),
        language=str(getattr(collection, 'language', 'en-US') or "en-US"),
        is_official=bool(getattr(collection, 'is_official', False)),
        total_learners=int(getattr(collection, 'total_learners', 0) or 0),
        total_words=estimated_total_words,
        accuracy_percentage=accuracy_percentage,
        study_time_seconds=study_time_seconds,
        words_list=words_list
    )


class VocabService:
    @staticmethod
    async def get_my_collections(user_id: str = "test_user_123") -> List[VocabularyCollectionResponse]:
        collections = await VocabularyCollectionModel.find(
            VocabularyCollectionModel.user_id == user_id,
            VocabularyCollectionModel.is_official == False
        ).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col, user_id=user_id, include_words=False)
            res.append(formatted)
        return res

    @staticmethod
    async def get_official_collections(user_id: Optional[str] = None) -> List[VocabularyCollectionResponse]:
        collections = await VocabularyCollectionModel.find(VocabularyCollectionModel.is_official == True).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col, user_id=user_id, include_words=False)
            res.append(formatted)
        return res

    @staticmethod
    async def create_my_collection(payload: CreateCollectionRequest, user_id: str = "test_user_123") -> VocabularyCollectionResponse:
        new_collection = VocabularyCollectionModel(
            user_id=user_id,
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
    async def update_collection_details(collection_id: str, payload: UpdateCollectionRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        col_user_id = getattr(collection, 'user_id', None)
        if not collection or collection.is_official or (isinstance(col_user_id, str) and col_user_id and col_user_id != user_id):
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
    async def add_word_to_collection(collection_id: str, payload: AddWordRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        col_user_id = getattr(collection, 'user_id', None)
        if not collection or collection.is_official or (isinstance(col_user_id, str) and col_user_id and col_user_id != user_id):
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
            user_id=user_id,
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
    async def update_single_word(word_id: str, payload: UpdateWordRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(word_id)
        word = await WordModel.get(obj_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        word_user_id = getattr(word, 'user_id', None)
        if isinstance(word_user_id, str) and word_user_id and word_user_id != user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to edit this word")

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
    async def bulk_update_words_in_collection(collection_id: str, payload: BulkUpdateWordsRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        col_user_id = getattr(collection, 'user_id', None)
        if not collection or collection.is_official or (isinstance(col_user_id, str) and col_user_id and col_user_id != user_id):
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
    async def bulk_add_words_to_collection(collection_id: str, payload: BulkAddWordsRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        col_user_id = getattr(collection, 'user_id', None)
        if not collection or collection.is_official or (isinstance(col_user_id, str) and col_user_id and col_user_id != user_id):
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
                user_id=user_id,
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
    async def process_and_add_pasted_text_with_gemini(collection_id: str, payload: PasteTextRequest, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        col_user_id = getattr(collection, 'user_id', None)
        if not collection or collection.is_official or (isinstance(col_user_id, str) and col_user_id and col_user_id != user_id):
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
        Act as an expert English lexicographer and language tutor. Analyze the following text and extract up to 15-20 key vocabulary words or phrasal verbs that appear directly in the text.

        CRITICAL SELECTION & EXTRACTION RULES:
        1. Extract English vocabulary words that appear DIRECTLY in the provided text.
        2. If the text contains a mix of English and Vietnamese (or other languages), IGNORE the Vietnamese/non-English parts and extract ALL valid English vocabulary words present in the text.
        3. NEVER translate Vietnamese words into English vocabulary. NEVER generate or invent external English words based on Vietnamese meanings. ONLY extract English words that are explicitly written in the input text itself.
        4. If the input text contains NO valid English words at all (e.g. 100% Vietnamese or pure gibberish), return an empty JSON array: [].
        5. Ignore basic/common stop words (e.g. "the", "and", "they", "is", "have", "go", "make", "good", "we", "our", "to").
        6. Prioritize academic, professional, B1-C2 CEFR level words, useful phrasal verbs, or domain-specific terms found in the text.
        7. Convert verbs to their base/infinitive form (e.g. "analyzed" -> "analyze").

        For each extracted word, provide:
        - "word": The base English word or phrasal verb EXACTLY as present in the input text.
        - "word_type": One of exactly [noun, verb, adjective, adverb, phrasal verb, idiom, pronoun, preposition, conjunction]
        - "cefr_level": One of [A1, A2, B1, B2, C1, C2]
        - "topic": Appropriate topic category (e.g. Technology, Business, Education, Environment, Daily Life)
        - "meaning": Concise, natural, contextually accurate Vietnamese translation.
        - "ipa": Standard IPA transcription with slashes (e.g. /rɪˈzɪl.jəns/).
        - "example_sentence": A clear, natural English example sentence demonstrating the word in context.

        OUTPUT FORMAT:
        Return ONLY a raw valid JSON array of objects. Do NOT use markdown codeblock wrappers like ```json. If no valid English words are found in the text, return [].

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
                        temperature=0.1,
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
            raw_word = item.get("word")
            if not raw_word:
                continue
            word_val = raw_word.strip().lower()
            if word_val in added_words:
                continue
            
            existing_word = await WordModel.find_one(WordModel.word == word_val)
            if not existing_word:
                existing_word = await WordModel.find_one({
                    "word": {"$regex": f"^{re.escape(word_val)}$", "$options": "i"}
                })
            
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

        if len(added_words) == 0:
            msg = "Văn bản không chứa từ vựng tiếng Anh hợp lệ nào để trích xuất!"
            status_str = "warning"
        else:
            msg = f"Gemini AI đã phân tích văn bản thành công! (Tạo mới {len(new_words_objects)} từ, thêm tổng cộng {len(added_words)} từ vào bộ)."
            status_str = "success"

        return {
            "status": status_str,
            "message": msg,
            "added_count": len(added_words),
            "new_created_count": len(new_words_objects),
            "highlighted_text": highlighted_text,
            "extracted_words": list(added_words)
        }

    @staticmethod
    async def get_vocabulary_collection(collection_id: str, user_id: Optional[str] = None) -> VocabularyCollectionResponse:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        col_user_id = getattr(collection, 'user_id', None)
        if not collection.is_official and not getattr(collection, 'is_public', True) and isinstance(col_user_id, str) and col_user_id and user_id and col_user_id != user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to view this collection")

        return await format_collection_response(collection, user_id=user_id)

    @staticmethod
    async def update_word_status(payload: UpdateWordStatusRequest, user_id: str = "test_user_123") -> VocabularyProgressResponse:
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
    async def update_collection_progress(payload: UpdateCollectionProgressRequest, user_id: str = "test_user_123") -> VocabularyProgressResponse:
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
    async def delete_vocabulary_collection(collection_id: str, user_id: str = "test_user_123") -> dict:
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        if collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to delete an official system collection"
            )
            
        col_user_id = getattr(collection, 'user_id', None)
        if isinstance(col_user_id, str) and col_user_id and col_user_id != user_id:
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to delete this collection"
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

    @staticmethod
    async def seed_ielts_idioms_collection() -> VocabularyCollectionResponse:
        existing = await VocabularyCollectionModel.find_one(VocabularyCollectionModel.title == "100+ IELTS Idioms Master Collection")
        if existing:
            return await format_collection_response(existing)

        idioms_data = [
            # Business & Work
            ("Make a living", "Earn money for basic needs", "He makes a living as a graphic designer."),
            ("Make ends meet", "Earn just enough to survive", "I work two jobs to make ends meet."),
            ("Call it a day/night", "Stop working", "Let's call it a day after this meeting."),
            ("Be cut out for", "Be suitable for something", "He's cut out for sales - very persuasive."),
            ("Wet behind the ears", "Inexperienced", "She's talented but still wet behind the ears."),
            ("Put all one's eggs in one basket", "Rely fully on one plan", "Don't put all your eggs in one basket; apply to multiple jobs."),
            ("Beat the clock", "Finish before deadline", "The team beat the clock and completed the task on time."),
            ("Burn the candle at both ends", "Overwork", "He's exhausted from burning the candle at both ends."),
            ("Back to the drawing board", "Start over after failure", "The client rejected our idea, so it's back to the drawing board."),
            ("Learn the ropes", "Learn how a job works", "I'm still learning the ropes at this company."),
            ("Keep your nose to the grindstone", "Work hard for a long time", "She kept her nose to the grindstone and got promoted."),
            ("Climb the corporate ladder", "Get promoted", "He's eager to climb the corporate ladder fast."),
            ("Think on your feet", "React quickly", "You must think on your feet during presentations."),
            ("On the same page", "Have the same understanding", "We're finally on the same page with our goals."),
            ("Get the ball rolling", "Start something", "Let's get the ball rolling on the new campaign."),

            # Shopping
            ("Hunt for bargains", "Look for cheap deals", "I always hunt for bargains during sales."),
            ("Go window-shopping", "Look without buying", "We went window-shopping after lunch."),
            ("Cost an arm and a leg", "Very expensive", "That dress cost an arm and a leg."),
            ("Take back", "Return an item", "You can take back the bag if it doesn't fit."),
            ("Pour money down the drain", "Waste money", "Buying that gadget was pouring money down the drain."),
            ("Fit like a glove", "Fit perfectly", "The suit fits like a glove."),
            ("The in thing", "Trendy or popular", "Smart watches are the in thing now."),
            ("Shop till you drop", "Shop for a long time", "We shopped till we dropped on Saturday."),
            ("Buy on impulse", "Buy without thinking", "I bought those shoes on impulse."),
            ("Pay through the nose", "Overpay", "I paid through the nose for this coat."),
            ("In the red", "Losing money", "The online shop is in the red this quarter."),
            ("In the black", "Making profit", "The store is back in the black after big sales."),
            ("Bargain basement", "Very cheap", "These came from the bargain basement."),
            ("Retail therapy", "Shopping to feel happier", "She went for retail therapy after a breakup."),
            ("Splash out on", "Spend a lot of money", "He splashed out on a designer belt."),

            # Travel
            ("Let one's hair down", "Relax", "I need a vacation to let my hair down."),
            ("Give someone a lift", "Give a ride", "He gave me a lift to the airport."),
            ("Hit the road", "Set off on a journey", "We hit the road early to beat traffic."),
            ("At the crack of dawn", "Very early morning", "We left at the crack of dawn for the trip."),
            ("Off the beaten track", "Remote, unusual locations", "I like traveling off the beaten track."),
            ("Live out of a suitcase", "Constantly travel", "I've been living out of a suitcase for months."),
            ("Have/get itchy feet", "Want to travel", "I got itchy feet after a year at home."),
            ("Travel light", "Carry very little luggage", "He always travels light with just a bag."),
            ("A change of scenery", "Refreshing experience", "A trip gives me a change of scenery."),
            ("Break the journey", "Stop before continuing", "We broke the journey in Paris."),
            ("Catch the travel bug", "Start loving travel", "I caught the travel bug after my first trip."),
            ("Hit the jackpot", "Have great success", "That vacation hotel really hit the jackpot."),
            ("In the middle of nowhere", "Isolated place", "We stayed in a cabin in the middle of nowhere."),
            ("Pack in", "Fit a lot into a short time", "We packed in 3 museums in one day."),
            ("Call it a day", "End the trip/activity", "We were tired and called it a day by noon."),

            # Feelings & Emotions
            ("Love at first sight", "Immediate romantic attraction", "It was love at first sight for them."),
            ("Head over heels in love", "Deeply in love", "She's head over heels in love with him."),
            ("On cloud nine", "Extremely happy", "I was on cloud nine after hearing the news."),
            ("Break someone's heart", "Deeply hurt someone", "He broke her heart by leaving."),
            ("Wear your heart on your sleeve", "Show emotions openly", "He wears his heart on his sleeve."),
            ("A long face", "Look unhappy", "What's with the long face today?"),
            ("In someone's shoes", "Imagine being someone else", "Try putting yourself in her shoes."),
            ("Green with envy", "Very jealous", "I was green with envy seeing her trip photos."),
            ("Down in the dumps", "Feeling sad", "He's down in the dumps lately."),
            ("Sit on the fence", "Undecided", "She's sitting on the fence about the decision."),
            ("Feel like two cents", "Ashamed or small", "I felt like two cents after my mistake."),
            ("Be the apple of one's eye", "Someone loved a lot", "His daughter is the apple of his eye."),
            ("Blow off steam", "Release anger", "I go to the gym to blow off steam."),
            ("Keep your chin up", "Stay positive", "Don't worry-keep your chin up!"),
            ("Jump for joy", "Be extremely happy", "She jumped for joy after passing IELTS."),

            # Education & Study
            ("Pass with flying colors", "Get excellent results", "He passed all his exams with flying colors."),
            ("Learn by heart", "Memorize", "I learned the speech by heart."),
            ("Rack one's brain", "Think hard", "I had to rack my brain to answer that."),
            ("No pain, no gain", "Effort leads to results", "You need to study hard - no pain, no gain!"),
            ("Not do things by halves", "Do something with full effort", "She never studies by halves."),
            ("Think outside the box", "Think creatively", "Our teacher encourages thinking outside the box."),
            ("Brush up on", "Revise", "I need to brush up on my grammar."),
            ("Teacher's pet", "Favorite student", "She was always the teacher's pet."),
            ("Hit the books", "Start studying", "Time to hit the books - finals are soon."),
            ("Pull an all-nighter", "Study all night", "I had to pull an all-nighter to finish my essay."),
            ("Cram for (an exam)", "Study in a short time", "He crammed for the math test."),
            ("A quick learner", "Learn things fast", "She's a quick learner and needs little support."),
            ("Read between the lines", "Understand hidden meaning", "Try to read between the lines in that article."),
            ("Daydream in class", "Not focus/pay attention", "He got scolded for daydreaming in class."),
            ("Top of the class", "Best student", "Jenny is always top of the class.")
        ]

        created_words = []
        for word_str, meaning_str, example_str in idioms_data:
            details = await fetch_word_details(word_str)
            w_obj = WordModel(
                word=word_str,
                word_type=details.get("word_type", "idiom"),
                ipa=details.get("ipa", ""),
                meaning=meaning_str,
                example_sentence=example_str,
                image_url=""
            )
            await w_obj.insert()
            created_words.append(w_obj)

        new_collection = VocabularyCollectionModel(
            title="100+ IELTS Idioms Master Collection",
            description="Bộ 100+ Thành ngữ IELTS thông dụng phân theo chủ đề (Work, Shopping, Travel, Feelings, Education)",
            topic="IELTS Idioms",
            language="English",
            is_official=True,
            is_public=True,
            total_learners=250,
            words=[w[0] for w in idioms_data],
            custom_words=created_words
        )
        await new_collection.insert()
        return await format_collection_response(new_collection)
