import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from beanie import init_beanie, PydanticObjectId
from httpx import AsyncClient, ASGITransport

from main import app
from models.WritingModel import WritingPromptModel, WritingSubmissionModel
from modules.User.user_util import UserUtil

@pytest.fixture(autouse=True, scope="session")
def init_mock_beanie():
    async def _init():
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={'ok': 1, 'version': '5.0.0'})
        mock_db.name = 'test_db'

        mock_collection = MagicMock()
        mock_collection.index_information = AsyncMock(return_value={})
        mock_collection.create_index = AsyncMock()
        mock_collection.create_indexes = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        await init_beanie(
            database=mock_db,
            document_models=[WritingPromptModel, WritingSubmissionModel]
        )

    asyncio.run(_init())

@pytest.fixture(autouse=True)
def override_jwt_auth():
    async def mock_protect():
        return {
            "id": "test_user_writing_123",
            "username": "testwritinguser",
            "email": "writing@example.com"
        }
    
    async def mock_protect_optional():
        return {
            "id": "test_user_writing_123",
            "username": "testwritinguser",
            "email": "writing@example.com"
        }

    app.dependency_overrides[UserUtil.Protect] = mock_protect
    app.dependency_overrides[UserUtil.ProtectOptional] = mock_protect_optional
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def sample_prompt():
    return WritingPromptModel(
        id=PydanticObjectId("650000000000000000000001"),
        title="Urban Dynamics: Heritage Architecture vs Modern Skyscrapers",
        task_type="WITH_GRAPH",
        task_description="Analyze the provided image depicting urban development.",
        reference_image_url="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab",
        ref_id="ARCH-204-URB",
        time_limit_minutes=45,
        word_count_target=250,
        suggested_structure=[{"section": "Introduction", "guide": "Hook & thesis"}],
        advanced_vocabulary=["Juxtaposition", "Obsolescence"]
    )

@pytest.mark.anyio
async def test_get_writing_prompts(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'find_all', return_value=MagicMock(to_list=AsyncMock(return_value=[sample_prompt])))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/writing/prompts")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["title"] == sample_prompt.title

@pytest.mark.anyio
async def test_get_writing_prompt_by_id(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        detail_res = await ac.get("/api/v1/writing/prompts/650000000000000000000001")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == "650000000000000000000001"
        assert "suggested_structure" in detail

@pytest.mark.anyio
async def test_ai_assistance_outline(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "prompt_id": "650000000000000000000001",
            "action": "OUTLINE"
        }
        res = await ac.post("/api/v1/writing/prompts/650000000000000000000001/ai-assistance", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "outline" in data

@pytest.mark.anyio
async def test_ai_assistance_collocations(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "prompt_id": "650000000000000000000001",
            "action": "COLLOCATIONS"
        }
        res = await ac.post("/api/v1/writing/prompts/650000000000000000000001/ai-assistance", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "suggestions" in data

@pytest.mark.anyio
async def test_submit_essay_empty_validation(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "prompt_id": "650000000000000000000001",
            "essay_content": "   ",
            "word_count": 0,
            "time_spent_seconds": 10
        }
        res = await ac.post("/api/v1/writing/sessions/submit", json=payload)
        assert res.status_code == 400
        error_msg = str(res.json().get("detail") or res.json().get("message") or "")
        assert "empty" in error_msg.lower()

@pytest.mark.anyio
async def test_submit_essay_and_4_criteria_grading(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    mocker.patch.object(WritingSubmissionModel, 'insert', AsyncMock(return_value=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "prompt_id": "650000000000000000000001",
            "essay_content": "Many experts believe that technology improve student engagement significantly. By providing interactive tools, it allows learners to identify their mistakes very fast.",
            "word_count": 26,
            "time_spent_seconds": 120
        }
        res = await ac.post("/api/v1/writing/sessions/submit", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "REVIEWED"
        assert data["overall_score"] > 0
        assert data["task_achievement_score"] > 0
        assert data["coherence_cohesion_score"] > 0
        assert data["lexical_resource_score"] > 0
        assert data["grammar_accuracy_score"] > 0
        assert len(data["highlight_spans"]) > 0

@pytest.mark.anyio
async def test_get_improved_essay_sample(mocker):
    mock_submission = WritingSubmissionModel(
        id=PydanticObjectId("650000000000000000000002"),
        user_id="test_user_writing_123",
        prompt_id="650000000000000000000001",
        prompt_title="Urban Dynamics",
        essay_content="Technology improve education very fast.",
        improved_essay_sample="Technology improves education instantaneously."
    )
    mocker.patch.object(WritingSubmissionModel, 'get', AsyncMock(return_value=mock_submission))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        imp_res = await ac.post("/api/v1/writing/sessions/650000000000000000000002/improved-sample")
        assert imp_res.status_code == 200
        data = imp_res.json()
        assert data["status"] == "success"
        assert "improved_essay" in data
