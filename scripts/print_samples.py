import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DATABASE_NAME", "omni_english_db")]

words = list(db["words"].find({}, {"word": 1, "meaning": 1, "ipa": 1}).limit(12))
print("==========================================================")
print("     MẪU DỮ LIỆU TỪ VỰNG SAU KHI LÀM SẠCH TRONG MONGODB    ")
print("==========================================================")
for w in words:
    print(f"• {w.get('word', ''):<20} | IPA: {w.get('ipa', ''):<18} | Nghĩa: {w.get('meaning', '')}")
print("==========================================================")
client.close()
