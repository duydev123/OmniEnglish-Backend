import os
import sys
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from models.VocabularyCollection import VocabularyCollectionModel, UserWordStatusModel, UserProgressModel
from models.Vocabulary import WordModel
from modules.Vocabulary.vocab_service import VocabService

async def main():
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DATABASE_NAME", "omni_english_db")
    print(f"Connecting to {db_name}...")
    client = AsyncIOMotorClient(mongo_uri)
    await init_beanie(
        database=client.get_database(db_name),
        document_models=[
            VocabularyCollectionModel,
            WordModel,
            UserWordStatusModel,
            UserProgressModel
        ]
    )
    official_cols = await VocabService.get_official_collections()
    print(f"Fetched {len(official_cols)} official collections!")
    if official_cols:
        print(f"Sample Collection Title: {official_cols[0].title}")
        print(f"Sample Collection Words Count: {len(official_cols[0].words_list)}")

if __name__ == "__main__":
    asyncio.run(main())
