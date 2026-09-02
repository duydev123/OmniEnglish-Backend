import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from google import genai

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "omni_english_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logger = logging.getLogger("OmniFastIPA")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(ch)

ai_client = genai.Client(api_key=GEMINI_API_KEY)

async def generate_batch_ipa(words_chunk: List[str], semaphore: asyncio.Semaphore) -> Dict[str, str]:
    async with semaphore:
        prompt = (
            "Provide official Cambridge/Oxford International Phonetic Alphabet (IPA) transcriptions for these English words/phrases.\n"
            "Output MUST be strict JSON dictionary mapping each word to its IPA: {\"word\": \"/IPA/\"}.\n\n"
            "Words list:\n" + json.dumps(words_chunk)
        )
        try:
            resp = await ai_client.aio.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            if resp.text:
                cleaned = resp.text.strip().replace("```json", "").replace("```", "")
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    return {k.strip().lower(): str(v).strip() for k, v in data.items() if v}
        except Exception as e:
            logger.warning(f"Batch generation error: {e}")
        return {}

async def main():
    logger.info("🚀 STARTING FAST PARALLEL IPA ENRICHER WITH GEMINI AI...")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DATABASE_NAME]
    words_col = db["words"]

    # Fetch missing docs
    query = {
        "$or": [
            {"ipa": {"$in": ["", None, "None"]}},
            {"ipa": {"$exists": False}}
        ]
    }

    missing_docs = list(words_col.find(query))
    logger.info(f"🔍 Found {len(missing_docs)} words missing IPA in database.")

    if not missing_docs:
        logger.info("🎉 ALL WORDS IN DATABASE ALREADY HAVE 100% IPA COVERAGE!")
        mongo_client.close()
        return

    word_map = {doc.get("word", "").strip().lower(): doc["_id"] for doc in missing_docs if doc.get("word")}
    all_words = list(word_map.keys())

    chunk_size = 50
    chunks = [all_words[i:i + chunk_size] for i in range(0, len(all_words), chunk_size)]
    logger.info(f"📦 Split {len(all_words)} words into {len(chunks)} parallel chunks of 50 words each.")

    semaphore = asyncio.Semaphore(10) # 10 parallel tasks
    tasks = [generate_batch_ipa(c, semaphore) for c in chunks]

    results = await asyncio.gather(*tasks)

    bulk_updates = []
    now_utc = datetime.now(timezone.utc)

    for res in results:
        for w_lower, ipa_val in res.items():
            if w_lower in word_map and ipa_val:
                doc_id = word_map[w_lower]
                formatted_ipa = ipa_val if ipa_val.startswith("/") else f"/{ipa_val}/"
                bulk_updates.append(UpdateOne({"_id": doc_id}, {"$set": {"ipa": formatted_ipa, "updated_at": now_utc}}))

    if bulk_updates:
        words_col.bulk_write(bulk_updates, ordered=False)
        logger.info(f"✅ SUCCESSFULLY UPDATED {len(bulk_updates)} WORDS WITH COMPLETE IPA IN MONGOBD!")

    remaining = words_col.count_documents(query)
    logger.info(f"📊 REMAINING UNTOUCHED WORDS: {remaining}")
    if remaining == 0:
        logger.info("🎉 GUARANTEED 100% IPA COVERAGE FOR ALL VOCABULARY IN DATABASE!")

    mongo_client.close()

if __name__ == "__main__":
    asyncio.run(main())
