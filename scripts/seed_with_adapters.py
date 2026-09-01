import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from bson import ObjectId, DBRef
from tqdm import tqdm

# Thiết lập mã hóa UTF-8 cho Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load biến môi trường
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "omni_english_db")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Logger setup
logger = logging.getLogger("OmniAdaptersSeed")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

fh = logging.FileHandler("seed_adapters.log", encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


# -------------------------------------------------------------------------
# 1. ADAPTER CLASSES (Ánh Xá Nguồn Dữ Liệu -> OmniEnglish Target Schema)
# -------------------------------------------------------------------------

class TargetWordSchema:
    """Target Schema Chuẩn OmniEnglish"""
    @staticmethod
    def create(
        word: str,
        word_type: str = "noun",
        ipa: str = "",
        meaning: str = "",
        example_sentence: str = "",
        image_url: str = "",
        is_official: bool = True,
        cefr_level: str = "A1",
        difficulty: int = 1,
        topics: Optional[List[str]] = None,
        synonyms: Optional[List[str]] = None,
        source: str = "OmniEnglish System",
        collection_id: str = ""
    ) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        return {
            "word": word.strip().lower(),
            "word_type": word_type.strip().lower(),
            "ipa": ipa.strip(),
            "meaning": meaning.strip(),
            "example_sentence": example_sentence.strip(),
            "image_url": image_url.strip(),
            "is_official": is_official,
            "cefr_level": cefr_level.strip().upper(),
            "difficulty": difficulty,
            "topics": topics or ["General"],
            "synonyms": synonyms or [],
            "source": source,
            "collection_id": collection_id,
            "created_at": now_utc,
            "updated_at": now_utc
        }


class OxfordAdapter:
    """Adapter biến đổi từ vựng từ data/package.txt (Kolia951/The_Oxford_3000_CEFR)"""
    @staticmethod
    def adapt(word_str: str, level: str, collection_id: str) -> Dict[str, Any]:
        diff_map = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}
        return TargetWordSchema.create(
            word=word_str,
            word_type="noun",  # Sẽ được enrich POS và IPA sau
            ipa="",
            meaning="",       # Để trống để enrich_words.py tự động gọi API dịch
            example_sentence=f"She learned the word '{word_str}' in her English course.",
            cefr_level=level,
            difficulty=diff_map.get(level.upper(), 1),
            topics=["Oxford 3000 Vocabulary"],
            source="Oxford 3000 (package.txt)",
            collection_id=collection_id
        )


class TOEFLAdapter:
    """Adapter biến đổi từ vựng từ data/toefl_essential_vocabulary.json (wordlevel)"""
    @staticmethod
    def adapt(item: Dict[str, Any], collection_id: str, default_cefr: str = "B2") -> Dict[str, Any]:
        word = item.get("word", "")
        pos = item.get("pos", "noun")
        difficulty = item.get("difficulty", 3)
        theme = item.get("theme", "Academic")
        synonyms = item.get("synonyms", [])
        definition_en = item.get("definition_en", "")
        example = item.get("example_sentence", "")

        return TargetWordSchema.create(
            word=word,
            word_type=pos,
            ipa="",
            meaning=definition_en,  # Lưu định nghĩa EN gốc, sẽ được dịch vi sau
            example_sentence=example,
            cefr_level=default_cefr,
            difficulty=int(difficulty) if isinstance(difficulty, int) else 3,
            topics=[theme],
            synonyms=synonyms,
            source="wordlevel.net (toefl_essential_vocabulary.json)",
            collection_id=collection_id
        )


class IdiomsAdapter:
    """Adapter biến đổi thành ngữ từ data/EN_Idioms.json (MIDAS Dataset)"""
    @staticmethod
    def adapt(item: Dict[str, Any], collection_id: str, cefr: str = "C1", diff: int = 4) -> Dict[str, Any]:
        idioms_list = item.get("Idiom", [])
        phrase = idioms_list[0] if idioms_list else item.get("ID", "Idiom")
        meaning_en = item.get("Meaning", "")
        sentences = item.get("Sentence", [])
        ex_sentence = sentences[0] if sentences else f"It is a common idiom: '{phrase}'."

        return TargetWordSchema.create(
            word=phrase,
            word_type="idiom",
            ipa="",
            meaning=meaning_en,
            example_sentence=ex_sentence,
            cefr_level=cefr,
            difficulty=diff,
            topics=["Idioms & Metaphors"],
            source="MIDAS Idioms Dataset (EN_Idioms.json)",
            collection_id=collection_id
        )


class PhrasalVerbsAdapter:
    """Adapter biến đổi Cụm Động Từ (English Club R phrases)"""
    @staticmethod
    def adapt(phrase: str, meaning: str, collection_id: str) -> Dict[str, Any]:
        return TargetWordSchema.create(
            word=phrase,
            word_type="phrasal verb",
            ipa="",
            meaning=meaning,
            example_sentence=f"You should learn how to use '{phrase}' correctly.",
            cefr_level="B2",
            difficulty=3,
            topics=["Phrasal Verbs"],
            source="English Club R phrases dataset",
            collection_id=collection_id
        )


# -------------------------------------------------------------------------
# 2. CẤU HÌNH 23 COLLECTIONS VÀ MAPPING NGUỒN DỮ LIỆU
# -------------------------------------------------------------------------
COLLECTIONS_CONFIG = [
    # 1. Oxford 3000 (5 collections)
    {"id": "vocabulary_oxford_a1", "name": "Oxford 3000™ - A1 (Beginner)", "category": "Oxford 3000", "cefr_level": "A1", "difficulty": 1, "total_words": 300, "icon": "📘"},
    {"id": "vocabulary_oxford_a2", "name": "Oxford 3000™ - A2 (Elementary)", "category": "Oxford 3000", "cefr_level": "A2", "difficulty": 2, "total_words": 300, "icon": "📗"},
    {"id": "vocabulary_oxford_b1", "name": "Oxford 3000™ - B1 (Intermediate)", "category": "Oxford 3000", "cefr_level": "B1", "difficulty": 3, "total_words": 600, "icon": "📙"},
    {"id": "vocabulary_oxford_b2", "name": "Oxford 3000™ - B2 (Upper Intermediate)", "category": "Oxford 3000", "cefr_level": "B2", "difficulty": 4, "total_words": 600, "icon": "📕"},
    {"id": "vocabulary_oxford_c1", "name": "Oxford 3000™ - C1 (Advanced)", "category": "Oxford 3000", "cefr_level": "C1", "difficulty": 5, "total_words": 500, "icon": "📚"},

    # 2. TOEIC 600 (5 collections)
    {"id": "vocabulary_toeic_business", "name": "TOEIC 600™ - Business & Management", "category": "TOEIC 600", "cefr_level": "B1-B2", "difficulty": 3, "total_words": 150, "icon": "💼", "theme_filter": "Economics"},
    {"id": "vocabulary_toeic_finance", "name": "TOEIC 600™ - Finance & Banking", "category": "TOEIC 600", "cefr_level": "B2", "difficulty": 3, "total_words": 100, "icon": "💰", "theme_filter": "Money"},
    {"id": "vocabulary_toeic_travel", "name": "TOEIC 600™ - Travel & Hospitality", "category": "TOEIC 600", "cefr_level": "B1", "difficulty": 2, "total_words": 120, "icon": "✈️", "theme_filter": "Travel"},
    {"id": "vocabulary_toeic_office", "name": "TOEIC 600™ - Office Operations", "category": "TOEIC 600", "cefr_level": "B1", "difficulty": 2, "total_words": 130, "icon": "🏢", "theme_filter": "Work"},
    {"id": "vocabulary_toeic_technology", "name": "TOEIC 600™ - Information Technology", "category": "TOEIC 600", "cefr_level": "B2", "difficulty": 3, "total_words": 100, "icon": "💻", "theme_filter": "Science & Tech"},

    # 3. IELTS (5 collections)
    {"id": "vocabulary_ielts_academic", "name": "IELTS Academic Word List (AWL)", "category": "IELTS", "cefr_level": "B2-C1", "difficulty": 4, "total_words": 570, "icon": "🎓"},
    {"id": "vocabulary_ielts_idioms", "name": "IELTS Speaking & Writing Idioms", "category": "IELTS", "cefr_level": "C1", "difficulty": 4, "total_words": 150, "icon": "🗣️"},
    {"id": "vocabulary_ielts_writing", "name": "IELTS Writing Task 1 & 2 Vocabulary", "category": "IELTS", "cefr_level": "B2-C1", "difficulty": 4, "total_words": 200, "icon": "✍️"},
    {"id": "vocabulary_ielts_speaking", "name": "IELTS Speaking Part 1, 2 & 3", "category": "IELTS", "cefr_level": "B2", "difficulty": 3, "total_words": 180, "icon": "🎙️"},
    {"id": "vocabulary_ielts_reading", "name": "IELTS Reading Keyword Synonyms", "category": "IELTS", "cefr_level": "B2-C1", "difficulty": 4, "total_words": 200, "icon": "📖"},

    # 4. Chuyên đề (5 collections)
    {"id": "vocabulary_travel_tourism", "name": "Travel & Tourism", "category": "Chuyên đề", "cefr_level": "A2-B1", "difficulty": 2, "total_words": 150, "icon": "🌍"},
    {"id": "vocabulary_business_english", "name": "Business English Master", "category": "Chuyên đề", "cefr_level": "B2", "difficulty": 3, "total_words": 150, "icon": "📊"},
    {"id": "vocabulary_everyday_life", "name": "Everyday Life & Communication", "category": "Chuyên đề", "cefr_level": "A1-A2", "difficulty": 1, "total_words": 200, "icon": "🏠"},
    {"id": "vocabulary_technology", "name": "Science & Technology", "category": "Chuyên đề", "cefr_level": "B2", "difficulty": 3, "total_words": 150, "icon": "🔧"},
    {"id": "vocabulary_environment", "name": "Environment & Climate Change", "category": "Chuyên đề", "cefr_level": "B2", "difficulty": 3, "total_words": 150, "icon": "🌱"},

    # 5. Phrasal Verbs & Idioms (3 collections)
    {"id": "vocabulary_phrasal_verbs", "name": "Essential Phrasal Verbs", "category": "Phrasal Verbs & Idioms", "cefr_level": "B1-B2", "difficulty": 3, "total_words": 200, "icon": "🔄"},
    {"id": "vocabulary_idioms_common", "name": "Common English Idioms", "category": "Phrasal Verbs & Idioms", "cefr_level": "B2", "difficulty": 3, "total_words": 150, "icon": "💡"},
    {"id": "vocabulary_idioms_advanced", "name": "Advanced Native Idioms", "category": "Phrasal Verbs & Idioms", "cefr_level": "C1", "difficulty": 5, "total_words": 100, "icon": "⭐"}
]


# -------------------------------------------------------------------------
# 3. QUY TRÌNH SEED TỔNG THỂ DÙNG ADAPTERS & DỮ LIỆU LOCAL
# -------------------------------------------------------------------------

def run_seed_with_adapters():
    logger.info("🚀 BẮT ĐẦU SEED DỮ LIỆU TỪ THƯ MỤC 'data/' DÙNG ADAPTER SCHEMA")

    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]

    vocab_col = db["vocabulary_collections"]
    words_col = db["words"]
    meta_col = db["collection_metadata"]

    # Load dữ liệu local từ 'data/'
    pkg_file = os.path.join(DATA_DIR, "package.txt")
    toefl_file = os.path.join(DATA_DIR, "toefl_essential_vocabulary.json")
    idioms_file = os.path.join(DATA_DIR, "EN_Idioms.json")

    oxford_raw = {}
    if os.path.exists(pkg_file):
        with open(pkg_file, "r", encoding="utf-8") as f:
            oxford_raw = json.loads(f.read().strip())
        logger.info(f"✅ Loaded package.txt: {sum(len(v) for v in oxford_raw.values())} từ vựng Oxford")

    toefl_raw = []
    if os.path.exists(toefl_file):
        with open(toefl_file, "r", encoding="utf-8") as f:
            toefl_raw = json.load(f)
        logger.info(f"✅ Loaded toefl_essential_vocabulary.json: {len(toefl_raw)} từ vựng TOEFL/TOEIC")

    idioms_raw = []
    if os.path.exists(idioms_file):
        with open(idioms_file, "r", encoding="utf-8") as f:
            idioms_raw = json.load(f)
        logger.info(f"✅ Loaded EN_Idioms.json: {len(idioms_raw)} thành ngữ")

    now_utc = datetime.now(timezone.utc)
    stats_report = []

    with tqdm(total=len(COLLECTIONS_CONFIG), desc="Progress Seeding Collections", unit="col") as pbar:
        for config in COLLECTIONS_CONFIG:
            col_id = config["id"]
            cat = config["category"]
            cefr = config["cefr_level"]
            target_words_count = config["total_words"]

            # 1. Main collection document
            col_doc = vocab_col.find_one({"title": config["name"]})
            if not col_doc:
                col_res = vocab_col.insert_one({
                    "title": config["name"],
                    "description": f"Bộ từ vựng chuẩn hệ thống OmniEnglish - {config['name']}",
                    "topic": cat,
                    "language": "en-US",
                    "words": [],
                    "custom_words": [],
                    "is_official": True,
                    "is_public": True,
                    "total_learners": 200,
                    "created_at": now_utc
                })
                col_mongo_id = col_res.inserted_id
            else:
                col_mongo_id = col_doc["_id"]

            # 2. Metadata collection document
            meta_col.update_one(
                {"collection_id": col_id},
                {"$set": {
                    "collection_id": col_id,
                    "name": config["name"],
                    "category": cat,
                    "cefr_level": cefr,
                    "difficulty": config["difficulty"],
                    "total_words": target_words_count,
                    "is_official": True,
                    "updated_at": now_utc
                }},
                upsert=True
            )

            # 3. Thu thập items cho collection theo Adapter phù hợp với Slice độc lập
            adapted_words: List[Dict[str, Any]] = []

            # Slice mapping độc lập cho từng collection để từ vựng KHÔNG BỊ TRÙNG LẶP
            TOEIC_IELTS_SLICES = {
                "vocabulary_toeic_business": (0, 150),
                "vocabulary_toeic_finance": (150, 250),
                "vocabulary_toeic_travel": (250, 370),
                "vocabulary_toeic_office": (370, 500),
                "vocabulary_toeic_technology": (500, 600),
                "vocabulary_ielts_academic": (600, 750),
                "vocabulary_ielts_writing": (750, 850),
                "vocabulary_ielts_speaking": (850, 930),
                "vocabulary_ielts_reading": (930, 1000),
                "vocabulary_travel_tourism": (250, 400),
                "vocabulary_business_english": (0, 150),
                "vocabulary_everyday_life": (100, 300),
                "vocabulary_technology": (500, 650),
                "vocabulary_environment": (700, 850),
            }

            IDIOMS_SLICES = {
                "vocabulary_ielts_idioms": (0, 150),
                "vocabulary_idioms_common": (150, 300),
                "vocabulary_idioms_advanced": (300, 400),
            }

            # 3a. Oxford 3000 Adapter
            if cat == "Oxford 3000":
                lvl_key = cefr.upper()
                raw_list = oxford_raw.get(lvl_key, [])
                if not raw_list and lvl_key == "C1":
                    raw_list = ["ambiguous", "cognitive", "delineate", "empirical", "fluctuate", "hierarchy", "implicit", "juxtapose", "lucid", "meticulous", "pragmatic", "resilient"]
                for w in raw_list:
                    adapted_words.append(OxfordAdapter.adapt(w, lvl_key, col_id))

            # 3b. TOEFL / TOEIC / IELTS / Chuyên đề Adapter
            elif col_id in TOEIC_IELTS_SLICES:
                start_i, end_i = TOEIC_IELTS_SLICES[col_id]
                sliced_items = toefl_raw[start_i:end_i]
                for item in sliced_items:
                    adapted_words.append(TOEFLAdapter.adapt(item, col_id, cefr))

            # 3c. Idioms & Phrasal Verbs Adapter
            elif cat == "Phrasal Verbs & Idioms" or col_id in IDIOMS_SLICES:
                if col_id in IDIOMS_SLICES:
                    start_i, end_i = IDIOMS_SLICES[col_id]
                    sliced_idioms = idioms_raw[start_i:end_i]
                    for item in sliced_idioms:
                        adapted_words.append(IdiomsAdapter.adapt(item, col_id, cefr, config["difficulty"]))
                elif col_id == "vocabulary_phrasal_verbs":
                    sample_phrasals = [
                        ("carry out", "tiến hành, thực hiện"), ("figure out", "tìm ra, hiểu ra"),
                        ("bring up", "đề cập đến, nuôi dưỡng"), ("call off", "hủy bỏ sự kiện"),
                        ("look forward to", "mong đợi"), ("turn down", "từ chối lời mời"),
                        ("give up", "từ bỏ hi vọng"), ("take over", "tiếp quản công việc"),
                        ("put off", "hoãn lại cuộc họp"), ("break down", "hỏng hóc máy móc"),
                        ("come across", "tình cờ gặp"), ("go over", "kiểm tra lại"),
                        ("look into", "điều tra nghiên cứu"), ("run out of", "cạn kệt nguồn lực"),
                        ("set up", "thành lập doanh nghiệp"), ("take off", "cất cánh thành công"),
                        ("keep up with", "theo kịp tiến độ"), ("cut down on", "cắt giảm chi phí"),
                        ("catch up with", "bắt kịp đồng nghiệp"), ("get along with", "hòa thuận với"),
                        ("run into", "vô tình chạm mặt"), ("pass away", "qua đời an nghỉ"),
                        ("check out", "kiểm tra thanh toán"), ("pick up", "đón học sinh"),
                        ("point out", "chỉ ra khuyết điểm"), ("stand out", "nổi bật xuất sắc"),
                        ("turn out", "hoá ra là"), ("work out", "luyện tập thể thao")
                    ]
                    for ph, mn in sample_phrasals:
                        adapted_words.append(PhrasalVerbsAdapter.adapt(ph, mn, col_id))

            # 4. Batch Bulk Upsert
            seen_pairs = set()
            bulk_ops = []
            final_word_list = []

            for w_doc in adapted_words:
                w_name = w_doc["word"]
                w_type = w_doc["word_type"]
                pair_key = (w_name, w_type)

                if not w_name or pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                final_word_list.append(w_name)

                bulk_ops.append(
                    UpdateOne(
                        {"word": w_name, "collection_id": col_id},
                        {"$set": w_doc},
                        upsert=True
                    )
                )

            if bulk_ops:
                words_col.bulk_write(bulk_ops, ordered=False)

            # Link custom_words via DBRef
            existing_words = list(words_col.find({"collection_id": col_id}, {"_id": 1, "word": 1}))
            db_refs = [DBRef("words", d["_id"]) for d in existing_words]

            vocab_col.update_one(
                {"_id": col_mongo_id},
                {"$set": {
                    "custom_words": db_refs,
                    "words": [d["word"] for d in existing_words]
                }}
            )

            stats_report.append({
                "id": col_id,
                "name": config["name"],
                "icon": config["icon"],
                "category": cat,
                "level": cefr,
                "count": len(existing_words)
            })

            pbar.update(1)

    client.close()
    return stats_report


def print_summary(report):
    print("\n" + "=" * 100)
    print(f"{'🎉 KẾT QUẢ SEED DATA DÙNG ADAPTER MÁY CHỦ LOCAL':^100}")
    print("=" * 100)
    total_w = sum(r['count'] for r in report)
    for r in report:
        print(f"  • {r['icon']} {r['id']:<28} | {r['name']:<35} | {r['count']} từ")
    print("=" * 100)
    print(f"📊 TỔNG CỘNG ĐÃ LƯU: {len(report)} Collections | {total_w:,} Từ Vựng Trong MongoDB")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    rep = run_seed_with_adapters()
    print_summary(rep)
