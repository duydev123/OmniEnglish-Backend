import os
import sys
import json
import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import httpx
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

# UTF-8 Encoding for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "omni_english_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logger = logging.getLogger("OmniIPAEnricher")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

fh = logging.FileHandler("enrich_ipa.log", encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

# -------------------------------------------------------------------------
# ARPAbet to IPA mapping dictionary
# -------------------------------------------------------------------------
ARPABET_TO_IPA = {
    "AA": "ɑ", "AA0": "ɑ", "AA1": "ˈɑ", "AA2": "ˌɑ",
    "AE": "æ", "AE0": "æ", "AE1": "ˈæ", "AE2": "ˌæ",
    "AH": "ʌ", "AH0": "ə", "AH1": "ˈʌ", "AH2": "ˌʌ",
    "AO": "ɔ", "AO0": "ɔ", "AO1": "ˈɔ", "AO2": "ˌɔ",
    "AW": "aʊ", "AW0": "aʊ", "AW1": "ˈaʊ", "AW2": "ˌaʊ",
    "AY": "aɪ", "AY0": "aɪ", "AY1": "ˈaɪ", "AY2": "ˌaɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð",
    "EH": "ɛ", "EH0": "ɛ", "EH1": "ˈɛ", "EH2": "ˌɛ",
    "ER": "ɜːr", "ER0": "ər", "ER1": "ˈɜːr", "ER2": "ˌɜːr",
    "EY": "eɪ", "EY0": "eɪ", "EY1": "ˈeɪ", "EY2": "ˌeɪ",
    "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IH0": "ɪ", "IH1": "ˈɪ", "IH2": "ˌɪ",
    "IY": "iː", "IY0": "i", "IY1": "ˈiː", "IY2": "ˌiː",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "oʊ", "OW0": "oʊ", "OW1": "ˈoʊ", "OW2": "ˌoʊ",
    "OY": "ɔɪ", "OY0": "ɔɪ", "OY1": "ˈɔɪ", "OY2": "ˌɔɪ",
    "P": "p", "R": "r", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ",
    "UH": "ʊ", "UH0": "ʊ", "UH1": "ˈʊ", "UH2": "ˌʊ",
    "UW": "uː", "UW0": "u", "UW1": "ˈuː", "UW2": "ˌuː",
    "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ"
}

def parse_arpabet_to_ipa(tags: List[str]) -> Optional[str]:
    """Convert ARPAbet pronunciation tags from Datamuse API to standard IPA format"""
    for t in tags:
        if t.startswith("pron:"):
            raw_ph = t.replace("pron:", "").strip().split()
            ipa_parts = []
            for token in raw_ph:
                ipa_char = ARPABET_TO_IPA.get(token.upper(), token.lower())
                ipa_parts.append(ipa_char)
            if ipa_parts:
                res = "".join(ipa_parts)
                return f"/{res}/"
    return None

# -------------------------------------------------------------------------
# API Helper Functions
# -------------------------------------------------------------------------
async def fetch_ipa_free_dict(client: httpx.AsyncClient, word: str) -> Optional[str]:
    """Tier 1: Free Dictionary API"""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word.strip())}"
    try:
        resp = await client.get(url, timeout=4.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                phonetics = data[0].get("phonetics", [])
                for ph in phonetics:
                    text = ph.get("text")
                    if text and text.startswith("/"):
                        return text
                if data[0].get("phonetic") and data[0].get("phonetic").startswith("/"):
                    return data[0].get("phonetic")
    except Exception:
        pass
    return None

async def fetch_ipa_datamuse(client: httpx.AsyncClient, word: str) -> Optional[str]:
    """Tier 2: Datamuse API"""
    url = f"https://api.datamuse.com/words?sp={urllib.parse.quote(word.strip())}&md=r"
    try:
        resp = await client.get(url, timeout=4.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                tags = data[0].get("tags", [])
                return parse_arpabet_to_ipa(tags)
    except Exception:
        pass
    return None

async def fetch_ipa_gemini_batch(words: List[str]) -> Dict[str, str]:
    """Tier 3: Gemini AI API Batch Generation for 100% IPA coverage"""
    if not words or not GEMINI_API_KEY:
        return {}
    
    try:
        from google import genai
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = (
            f"Provide official Cambridge/Oxford International Phonetic Alphabet (IPA) transcriptions for the following English words/phrases.\n"
            f"Return STRICT JSON mapping format: {{\"word\": \"/IPA/\"}}.\n\n"
            f"Words list:\n" + json.dumps(words)
        )

        resp = await ai_client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        
        if resp.text:
            cleaned = resp.text.strip().replace("```json", "").replace("```", "")
            res_dict = json.loads(cleaned)
            if isinstance(res_dict, dict):
                return {k.strip().lower(): str(v).strip() for k, v in res_dict.items() if v}
    except Exception as e:
        logger.warning(f"Gemini IPA Batch Generation Error: {e}")
    return {}

# -------------------------------------------------------------------------
# Main Execution Pipeline
# -------------------------------------------------------------------------
async def enrich_all_vocabulary_ipa():
    logger.info("🚀 BẮT ĐẦU TIẾN TRÌNH BỔ SUNG 100% IPA CHO TOÀN BỘ TỪ VỰNG TRONG DB")

    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    words_col = db["words"]

    # Query all words missing IPA or with empty/null IPA
    query = {
        "$or": [
            {"ipa": {"$in": ["", None]}},
            {"ipa": {"$exists": False}},
            {"ipa": "None"}
        ]
    }

    missing_docs = list(words_col.find(query))
    total_missing = len(missing_docs)

    logger.info(f"🔍 Tìm thấy tổng cộng {total_missing} từ vựng chưa có IPA trong database!")

    if total_missing == 0:
        logger.info("🎉 TẤT CẢ TỪ VỰNG TRONG DATABASE ĐÃ CÓ ĐẦY ĐỦ 100% IPA!")
        mongo_client.close()
        return

    bulk_updates = []
    success_cnt = 0
    remaining_words_for_gemini = []
    word_doc_map = {}

    async with httpx.AsyncClient(headers={"User-Agent": "OmniIPA/1.0"}) as http_client:
        with tqdm(total=total_missing, desc="Processing Tier 1 & 2 IPA", unit="word") as pbar:
            for doc in missing_docs:
                w_id = doc["_id"]
                w_str = doc.get("word", "").strip()
                if not w_str:
                    pbar.update(1)
                    continue

                word_doc_map[w_str.lower()] = w_id

                # Tier 1: Free Dictionary API
                ipa = await fetch_ipa_free_dict(http_client, w_str)
                
                # Tier 2: Datamuse API fallback
                if not ipa:
                    ipa = await fetch_ipa_datamuse(http_client, w_str)

                if ipa:
                    bulk_updates.append(UpdateOne({"_id": w_id}, {"$set": {"ipa": ipa, "updated_at": datetime.now(timezone.utc)}}))
                    success_cnt += 1
                else:
                    remaining_words_for_gemini.append(w_str)

                pbar.update(1)
                await asyncio.sleep(0.02)

    # Execute Tier 1 & Tier 2 Bulk Updates
    if bulk_updates:
        words_col.bulk_write(bulk_updates, ordered=False)
        logger.info(f"✅ [Tier 1 & 2] Đã cập nhật IPA thành công cho {len(bulk_updates)} từ vựng!")

    # Tier 3: Batch Gemini AI for any remaining words
    if remaining_words_for_gemini:
        logger.info(f"🤖 [Tier 3] Sử dụng Gemini AI để sinh IPA cho {len(remaining_words_for_gemini)} từ còn lại...")
        batch_size = 50
        gemini_bulk_updates = []

        for i in range(0, len(remaining_words_for_gemini), batch_size):
            chunk = remaining_words_for_gemini[i:i + batch_size]
            gemini_results = await fetch_ipa_gemini_batch(chunk)
            
            for w_clean, ipa_val in gemini_results.items():
                if w_clean in word_doc_map and ipa_val:
                    w_id = word_doc_map[w_clean]
                    # Ensure IPA format wraps with slashes
                    formatted_ipa = ipa_val if ipa_val.startswith("/") else f"/{ipa_val}/"
                    gemini_bulk_updates.append(UpdateOne({"_id": w_id}, {"$set": {"ipa": formatted_ipa, "updated_at": datetime.now(timezone.utc)}}))
                    success_cnt += 1
            
            await asyncio.sleep(0.5)

        if gemini_bulk_updates:
            words_col.bulk_write(gemini_bulk_updates, ordered=False)
            logger.info(f"✨ [Tier 3] Gemini AI đã bổ sung IPA cho thêm {len(gemini_bulk_updates)} từ vựng!")

    # Final Audit Check
    final_remaining = words_col.count_documents(query)
    logger.info(f"📊 BÁO CÁO TỔNG KẾT:")
    logger.info(f"   - Số từ vừa được bổ sung IPA: {success_cnt}")
    logger.info(f"   - Số từ còn thiếu IPA trong CSDL: {final_remaining}")

    if final_remaining == 0:
        logger.info("🎉 XÁC NHẬN 100% TỪ VỰNG TRONG DATABASE ĐÃ CÓ PHÁT ÂM IPA CHUẨN!")

    mongo_client.close()

if __name__ == "__main__":
    asyncio.run(enrich_all_vocabulary_ipa())
