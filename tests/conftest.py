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
from models.User import UserModel, DailyActivityLogModel
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
from models.VocabularyCollection import VocabularyCollectionModel, UserWordStatusModel, UserProgressModel
from models.Vocabulary import WordModel
from models.Writing import WritingPromptModel, WritingSubmissionModel
from models.Speaking import SpeakingTopicModel, SpeakingPromptModel, UserSpeakingTestSessionModel, ShadowingSentenceModel

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
            DailyActivityLogModel,
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
            VocabularyCollectionModel,
            WordModel,
            UserWordStatusModel,
            UserProgressModel,
            WritingPromptModel,
            WritingSubmissionModel,
            SpeakingTopicModel,
            SpeakingPromptModel,
            UserSpeakingTestSessionModel,
            ShadowingSentenceModel,
        ]
    )
    yield db

@pytest.fixture(autouse=True)
async def clean_database():
    import inspect
    db = mock_client.get_database("omni_english_db")
    collections = await db.list_collection_names()  # type: ignore
    for col in collections:
        if not col.startswith("system."):
            res = db[col].delete_many({})
            if inspect.isawaitable(res):
                await res
    yield db

@pytest.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    from fastapi import Request, HTTPException
    from modules.User.user_util import UserUtil

    async def mock_protect(request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = UserUtil.decode_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn!")
            return payload
        return {"_id": "60c72b2f9b1d8e1d88ef5567", "email": "mock@example.com"}

    async def mock_protect_optional(request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = UserUtil.decode_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn!")
            return payload
        return {"_id": "60c72b2f9b1d8e1d88ef5567", "email": "mock@example.com"}

    app.dependency_overrides[UserUtil.Protect] = mock_protect
    app.dependency_overrides[UserUtil.ProtectOptional] = mock_protect_optional

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
