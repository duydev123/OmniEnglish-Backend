import os
import sys
import re
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "omni_english_db")

VALID_WORD_TYPES = {"noun", "verb", "adjective", "adverb", "phrasal verb", "idiom", "pronoun", "preposition", "conjunction", "interjection"}

def clean_word_type(val):
    if not val:
        return "noun"
    v_str = str(val).lower().strip()
    if v_str in VALID_WORD_TYPES:
        return v_str
    # Split compound types like 'noun/verb/adjective'
    parts = re.split(r"[/,;\s]+", v_str)
    for p in parts:
        p = p.strip()
        if p in VALID_WORD_TYPES:
            return p
        if p.startswith("noun"): return "noun"
        if p.startswith("verb"): return "verb"
        if p.startswith("adj"): return "adjective"
        if p.startswith("adv"): return "adverb"
        if p.startswith("phrasal"): return "phrasal verb"
        if p.startswith("idiom"): return "idiom"
    return "noun"

def main():
    print(f"Cleaning invalid word_types in {DATABASE_NAME}.words...")
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    words_col = db["words"]

    docs = list(words_col.find({}, {"_id": 1, "word_type": 1}))
    bulk_ops = []
    fixed_cnt = 0

    for d in docs:
        old_wt = d.get("word_type")
        new_wt = clean_word_type(old_wt)
        if old_wt != new_wt:
            bulk_ops.append(
                UpdateOne({"_id": d["_id"]}, {"$set": {"word_type": new_wt}})
            )
            fixed_cnt += 1

    if bulk_ops:
        words_col.bulk_write(bulk_ops, ordered=False)
        print(f"✅ Successfully cleaned {fixed_cnt} invalid word_type fields in MongoDB!")
    else:
        print("✅ All word_type fields are already valid!")

    client.close()

if __name__ == "__main__":
    main()
