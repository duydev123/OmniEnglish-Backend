import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId, DBRef

# Force UTF-8 encoding for Windows console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

DEFAULT_MONGO_URI = "mongodb+srv://omni_english_db:duy123@cluster0.0clx1qx.mongodb.net/?appName=Cluster0"
DEFAULT_DB_NAME = "omni_english_db"

MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
DATABASE_NAME = os.getenv("DATABASE_NAME", DEFAULT_DB_NAME)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "ielts_speaking_pdf_topics.json")

# Logger Setup
logger = logging.getLogger("SpeakingPDFSeed")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


def seed_speaking_data():
    if not os.path.exists(DATA_FILE):
        logger.error(f"File data không tồn tại tại: {DATA_FILE}")
        sys.exit(1)

    logger.info(f"Connecting to MongoDB at: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]

    topics_col = db["speaking_topics"]
    prompts_col = db["speaking_prompts"]

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        topics_data = json.load(f)

    logger.info(f"Loaded {len(topics_data)} topics from JSON file.")

    total_topics_inserted = 0
    total_prompts_inserted = 0

    for item in topics_data:
        topic_info = item.get("topic", {})
        prompts_info = item.get("prompts", [])

        title = topic_info.get("title")
        if not title:
            continue

        now_utc = datetime.now(timezone.utc)

        # Upsert SpeakingTopicModel
        existing_topic = topics_col.find_one({"title": title})
        if existing_topic:
            topic_id = existing_topic["_id"]
            logger.info(f"Topic existing: '{title}' (ID: {topic_id}). Updating info...")
            topics_col.update_one(
                {"_id": topic_id},
                {
                    "$set": {
                        "description": topic_info.get("description"),
                        "tags": topic_info.get("tags", []),
                        "is_full_test": topic_info.get("is_full_test", False),
                        "updated_at": now_utc
                    }
                }
            )
        else:
            topic_doc = {
                "title": title,
                "description": topic_info.get("description"),
                "tags": topic_info.get("tags", []),
                "is_full_test": topic_info.get("is_full_test", False),
                "created_at": now_utc
            }
            res = topics_col.insert_one(topic_doc)
            topic_id = res.inserted_id
            total_topics_inserted += 1
            logger.info(f"Inserted new Topic: '{title}' (ID: {topic_id})")

        # Insert prompts for this topic
        for prompt in prompts_info:
            question_text = prompt.get("question_text")
            if not question_text:
                continue

            existing_prompt = prompts_col.find_one({
                "topic_id": DBRef("speaking_topics", topic_id),
                "question_text": question_text
            })

            prompt_doc = {
                "topic_id": DBRef("speaking_topics", topic_id),
                "part": prompt.get("part", "PART_1"),
                "sub_topic": prompt.get("sub_topic", ""),
                "question_text": question_text,
                "useful_vocabulary": prompt.get("useful_vocabulary", []),
                "ielts_tips": prompt.get("ielts_tips", []),
                "examiner_tip": prompt.get("examiner_tip", ""),
                "response_structure": prompt.get("response_structure", []),
                "created_at": now_utc
            }

            if existing_prompt:
                prompts_col.update_one({"_id": existing_prompt["_id"]}, {"$set": prompt_doc})
            else:
                prompts_col.insert_one(prompt_doc)
                total_prompts_inserted += 1

    logger.info("==================================================")
    logger.info(f"COMPLETED! New Topics Inserted: {total_topics_inserted}")
    logger.info(f"COMPLETED! New Prompts Inserted: {total_prompts_inserted}")
    logger.info("==================================================")

if __name__ == "__main__":
    seed_speaking_data()
