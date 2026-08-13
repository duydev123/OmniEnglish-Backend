import asyncio
import os
import pytest
from unittest.mock import patch
from mongomock_motor import AsyncMongoMockClient

# Thiết lập biến môi trường test để tránh ảnh hưởng đến DB thật và các cấu hình khác
os.environ["SECRET_KEY"] = "TEST_SECRET_KEY_FOR_JWT_SECURITY_MUST_BE_LARGE"
os.environ["MONGO_URI"] = "mongodb://localhost:27017/test_db"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:5173"

# Mock AsyncIOMotorClient trước khi import app từ main
mock_client = AsyncMongoMockClient()
patcher = patch("main.AsyncIOMotorClient", return_value=mock_client)
patcher.start()

from main import app
from beanie import init_beanie

# Import các models
from models.UserModel import UserModel
from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel,
    ReadingVocabularyBookmarkModel
)
from models.Listening import (
    ListeningPassageModel,
    ListeningAudioSegmentModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def init_beanie_db(event_loop):
    db = mock_client.get_database("omni_english_db")
    await init_beanie(
        database=db,
        document_models=[
            UserModel,
            ReadingPassageModel,
            ReadingMultipleChoiceModel,
            ReadingHeadingMatchingModel,
            ReadingFillBlankModel,
            ReadingTrueFalseNotGivenModel,
            UserReadingSessionModel,
            ReadingVocabularyBookmarkModel,
            ListeningPassageModel,
            ListeningAudioSegmentModel,
            ListeningMultipleChoiceModel,
            ListeningCompletionModel,
            UserListeningSessionModel,
        ]
    )
    yield db

@pytest.fixture(autouse=True)
async def clean_database():
    db = mock_client.get_database("omni_english_db")
    collections = await db.list_collection_names()
    for col in collections:
        if not col.startswith("system."):
            await db[col].delete_many({})
    yield db

@pytest.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
