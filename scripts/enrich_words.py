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

# Thiết lập mã hóa UTF-8 cho Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load biến môi trường
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "omni_english_db")

# Logger Setup
logger = logging.getLogger("OmniEnrich")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

fh = logging.FileHandler("enrich_words.log", encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


# -------------------------------------------------------------------------
# API Helper Functions (IPA & Dịch tiếng Việt)
# -------------------------------------------------------------------------

async def fetch_ipa_free_dict(client: httpx.AsyncClient, word: str) -> Optional[str]:
    """Gọi API Free Dictionary API lấy phát âm IPA chuẩn"""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
    try:
        resp = await client.get(url, timeout=4.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                phonetics = data[0].get("phonetics", [])
                for ph in phonetics:
                    if ph.get("text"):
                        return ph.get("text")
                if data[0].get("phonetic"):
                    return data[0].get("phonetic")
    except Exception:
        pass
    return None


async def fetch_vietnamese_translation(client: httpx.AsyncClient, text: str) -> Optional[str]:
    """Gọi API dịch tự động sang tiếng Việt qua MyMemory hoặc Google Translate free endpoint"""
    if not text:
        return None
    
    # Clean up text
    clean_text = text.strip()
    if len(clean_text) > 300:
        clean_text = clean_text[:300]

    # 1. Thử Google Translate GTX Endpoint
    gtx_url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={urllib.parse.quote(clean_text)}"
    try:
        resp = await client.get(gtx_url, timeout=4.0)
        if resp.status_code == 200:
            res_data = resp.json()
            if isinstance(res_data, list) and len(res_data) > 0 and isinstance(res_data[0], list):
                translated_pieces = [piece[0] for piece in res_data[0] if piece and piece[0]]
                if translated_pieces:
                    return "".join(translated_pieces).strip()
    except Exception:
        pass

    # 2. Thử MyMemory Endpoint làm fallback
    mymemory_url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair=en|vi"
    try:
        resp = await client.get(mymemory_url, timeout=4.0)
        if resp.status_code == 200:
            res_data = resp.json()
            match = res_data.get("responseData", {}).get("translatedText")
            if match and "MYMEMORY WARNING" not in match:
                return match.strip()
    except Exception:
        pass

    return None


# -------------------------------------------------------------------------
# Tiến Trình Enrich Từ Vựng Trong MongoDB
# -------------------------------------------------------------------------

async def enrich_vocabulary_database(limit_batch: int = 500):
    logger.info(f"🚀 BẮT ĐẦU TIẾN TRÌNH ENRICH BỔ SUNG IPA & NGHĨA TIẾNG VIỆT CHO DATABASE")

    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    words_col = db["words"]

    # Tìm các từ chưa có IPA hoặc chưa có Nghĩa tiếng Việt
    query = {
        "$or": [
            {"ipa": {"$in": ["", None]}},
            {"meaning": {"$in": ["", None]}},
            {"meaning": {"$regex": "^Nghĩa từ vựng|^She learned|^This is an example"}} # Nghĩa tạm
        ]
    }

    target_docs = list(words_col.find(query).limit(limit_batch))
    total_target = len(target_docs)

    if total_target == 0:
        logger.info("🎉 Tất cả từ vựng trong CSDL đã có đầy đủ IPA và nghĩa tiếng Việt!")
        mongo_client.close()
        return

    logger.info(f"🔍 Tìm thấy {total_target} từ vựng cần bổ sung IPA và dịch nghĩa...")

    success_ipa_cnt = 0
    success_vi_cnt = 0
    bulk_updates = []
    now_utc = datetime.now(timezone.utc)

    async with httpx.AsyncClient(headers={"User-Agent": "OmniEnglishBot/1.0"}) as http_client:
        with tqdm(total=total_target, desc="Enriching IPA & Vi Meaning", unit="word") as pbar:
            for doc in target_docs:
                w_id = doc["_id"]
                w_str = doc["word"]
                existing_ipa = doc.get("ipa", "")
                existing_meaning = doc.get("meaning", "")

                updates = {}

                # 1. Enrich IPA nếu thiếu
                if not existing_ipa or existing_ipa.startswith("/"):
                    new_ipa = await fetch_ipa_free_dict(http_client, w_str)
                    if new_ipa:
                        updates["ipa"] = new_ipa
                        success_ipa_cnt += 1

                # 2. Enrich Nghĩa tiếng Việt nếu thiếu hoặc là câu tiếng Anh tạm
                needs_vi_translation = False
                if not existing_meaning:
                    needs_vi_translation = True
                elif any(existing_meaning.startswith(prefix) for prefix in ["Nghĩa từ vựng", "She learned", "This is an example"]):
                    needs_vi_translation = True
                elif existing_meaning and not any(ord(char) > 127 for char in existing_meaning):
                    # Nếu nghĩa hiện tại là tiếng Anh hoàn toàn (definition_en), cần dịch sang vi
                    needs_vi_translation = True

                if needs_vi_translation:
                    source_text = existing_meaning if (existing_meaning and not existing_meaning.startswith("Nghĩa từ")) else w_str
                    vi_translation = await fetch_vietnamese_translation(http_client, source_text)
                    if vi_translation:
                        updates["meaning"] = vi_translation
                        success_vi_cnt += 1

                if updates:
                    updates["updated_at"] = now_utc
                    bulk_updates.append(
                        UpdateOne({"_id": w_id}, {"$set": updates})
                    )

                pbar.update(1)
                # Rate limit nhẹ để tránh bị block API miễn phí
                await asyncio.sleep(0.05)

    if bulk_updates:
        words_col.bulk_write(bulk_updates, ordered=False)
        logger.info(f"✅ Đã ghi thành công {len(bulk_updates)} bản ghi cập nhật vào MongoDB!")

    logger.info(f"📊 BÁO CÁO HOÀN THÀNH: Bổ sung thành công {success_ipa_cnt} IPA và {success_vi_cnt} nghĩa tiếng Việt!")
    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(enrich_vocabulary_database(limit_batch=300))
