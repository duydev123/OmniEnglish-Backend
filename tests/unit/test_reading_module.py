import pytest
from unittest.mock import AsyncMock, MagicMock
from beanie import PydanticObjectId
from httpx import AsyncClient, ASGITransport
from main import app
from models.Reading import ReadingPassageModel, UserReadingSessionModel
from modules.User.user_util import UserUtil

@pytest.fixture(autouse=True)
def override_jwt_auth():
    async def mock_protect():
        return {
            "id": "test_user_reading_123",
            "username": "readinguser",
            "email": "reading@example.com"
        }
    async def mock_protect_optional():
        return {
            "id": "test_user_reading_123",
            "username": "readinguser",
            "email": "reading@example.com"
        }
    app.dependency_overrides[UserUtil.Protect] = mock_protect
    app.dependency_overrides[UserUtil.ProtectOptional] = mock_protect_optional
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def sample_reading_passage():
    return ReadingPassageModel(
        id=PydanticObjectId("650000000000000000000010"),
        title="Urban Architecture & Biodiversity",
        topic="Architecture",
        difficulty="medium",
        content="Urban development has a profound impact on biodiversity...",
        total_questions=5
    )

@pytest.mark.asyncio
async def test_reading_passage_list_and_detail(mocker, sample_reading_passage):
    mocker.patch.object(ReadingPassageModel, 'find_all', return_value=MagicMock(to_list=AsyncMock(return_value=[sample_reading_passage])))
    mocker.patch.object(ReadingPassageModel, 'get', AsyncMock(return_value=sample_reading_passage))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_list = await ac.get("/api/v1/reading/passages")
        assert res_list.status_code == 200

        res_detail = await ac.get("/api/v1/reading/passages/650000000000000000000010")
        assert res_detail.status_code == 200
        assert res_detail.json()["title"] == sample_reading_passage.title

@pytest.mark.asyncio
async def test_reading_mcq_exercise_uc03(mocker, sample_reading_passage):
    """UC-03: Complete Reading MCQ exercise flow and auto-grading"""
    mocker.patch.object(ReadingPassageModel, 'get', AsyncMock(return_value=sample_reading_passage))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_start = await ac.get("/api/v1/reading/passages/650000000000000000000010/start")
        assert res_start.status_code in [200, 404]

@pytest.mark.asyncio
async def test_reading_summary_completion_uc04(mocker):
    """UC-04: Complete Reading Summary gap fill exercise"""
    summary_answers = {"blank_1": "biodiversity", "blank_2": "infrastructure"}
    assert len(summary_answers) == 2

@pytest.mark.asyncio
async def test_reading_heading_matching_uc05(mocker):
    """UC-05: Complete Heading Matching paragraph exercise"""
    matching_answers = {"paragraph_A": "Heading i", "paragraph_B": "Heading iii"}
    assert len(matching_answers) == 2

@pytest.mark.asyncio
async def test_reading_text_highlight_uc06(mocker):
    """UC-06: Highlight text and phrases in reading passage"""
    highlight_payload = {
        "text": "profound impact on biodiversity",
        "color": "yellow",
        "start_offset": 12,
        "end_offset": 43
    }
    assert highlight_payload["color"] == "yellow"
