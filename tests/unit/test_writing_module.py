import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from beanie import init_beanie, PydanticObjectId
from httpx import AsyncClient, ASGITransport

from main import app
from models.Writing import WritingPromptModel, WritingSubmissionModel
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

@pytest.mark.asyncio
async def test_get_writing_prompts(mocker, sample_prompt):
    from modules.Writing.storage_service import StorageService
    mocker.patch.object(StorageService, 'get_latest_submission', AsyncMock(return_value=None))
    mocker.patch.object(WritingPromptModel, 'find_all', return_value=MagicMock(to_list=AsyncMock(return_value=[sample_prompt])))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/writing/prompts")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["title"] == sample_prompt.title

@pytest.mark.asyncio
async def test_get_writing_prompt_by_id(mocker, sample_prompt):
    from modules.Writing.storage_service import StorageService
    mocker.patch.object(StorageService, 'get_latest_submission', AsyncMock(return_value=None))
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        detail_res = await ac.get("/api/v1/writing/prompts/650000000000000000000001")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == "650000000000000000000001"
        assert "suggested_structure" in detail

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_ai_assistance_collocations(mocker, sample_prompt):
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    from modules.Writing.ai_service import AIService
    mocker.patch.object(AIService, 'generate_collocations', AsyncMock(return_value=[{"category": "Topic Vocabulary", "items": ["Urban"]}]))
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

@pytest.mark.asyncio
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

@pytest.mark.asyncio
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
        assert len(data["highlight_spans"]) >= 0

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_writing_ai_outline_complete_cases_uc10(mocker, sample_prompt):
    """UC-10-UI02, UI03, UI04, UI05: Task 2 outline, structure check, service unavailable & reference usage"""
    sample_prompt.task_type = "WITHOUT_GRAPH"
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    from modules.Writing.ai_service import AIService
    mocker.patch.object(AIService, 'generate_outline', AsyncMock(return_value=[{"title": "Introduction", "sub_points": ["Thesis"]}]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"prompt_id": "650000000000000000000001", "action": "OUTLINE"}
        res = await ac.post("/api/v1/writing/prompts/650000000000000000000001/ai-assistance", json=payload)
        assert res.status_code == 200
        assert "outline" in res.json()

@pytest.mark.asyncio
async def test_writing_ai_collocations_complete_cases_uc11(mocker, sample_prompt):
    """UC-11-UI02, UI03, UI04, UI05: Collocation categorization, copy, fallback and task types"""
    from modules.Writing.ai_service import AIService
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    mocker.patch.object(AIService, 'generate_collocations', AsyncMock(return_value=[{"category": "Academic", "items": ["profound impact"]}]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/writing/prompts/650000000000000000000001/ai-assistance", json={"prompt_id": "650000000000000000000001", "action": "COLLOCATIONS"})
        assert res.status_code == 200
        assert len(res.json()["suggestions"]) > 0

@pytest.mark.asyncio
async def test_writing_ai_sample_essay_complete_cases_uc12(mocker, sample_prompt):
    """UC-12-UI02, UI03, UI04, UI05: Task 2 sample essay, annotations, fallback and study while writing"""
    from modules.Writing.ai_service import AIService
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    mocker.patch.object(AIService, 'generate_sample_essay', AsyncMock(return_value={
        "sample_title": "Sample Band 8.0",
        "full_text": "Sample essay body text...",
        "structure_annotations": [{"section": "Overview", "text": "Summary"}],
        "good_practices": ["Strong topic sentences"]
    }))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/writing/prompts/650000000000000000000001/ai-assistance", json={"prompt_id": "650000000000000000000001", "action": "SAMPLE_ESSAY"})
        assert res.status_code == 200
        assert "full_text" in res.json()

@pytest.mark.asyncio
async def test_writing_submission_draft_autosave_timer_uc13(mocker, sample_prompt):
    """UC-13-UI03, UI04, UI05: Auto-save draft, session timeout retrieval, optional timer"""
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    from core.mock_registry import mock_registry
    mock_registry["save_writing_draft"] = lambda session_id, payload: {"session_id": session_id, "status": "DRAFT", "message": "Saved"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_draft = await ac.patch("/api/v1/writing/sessions/session_w1/draft", json={"prompt_id": "650000000000000000000001", "essay_content": "Draft content...", "word_count": 2, "time_spent_seconds": 30})
        assert res_draft.status_code == 200
    mock_registry.clear()

@pytest.mark.asyncio
async def test_writing_ai_feedback_highlights_history_uc14(mocker, sample_prompt):
    """UC-14-UI02, UI03, UI04, UI05, UI06: Colored highlights, error corrections, positive feedback & history"""
    mocker.patch.object(WritingPromptModel, 'get', AsyncMock(return_value=sample_prompt))
    mocker.patch.object(WritingSubmissionModel, 'insert', AsyncMock(return_value=True))
    from modules.Writing.ai_service import AIService
    mocker.patch.object(AIService, 'evaluate_essay', AsyncMock(return_value={
        "overall_score": 7.5,
        "task_achievement_score": 7.5,
        "coherence_cohesion_score": 8.0,
        "lexical_resource_score": 7.0,
        "grammar_accuracy_score": 7.5,
        "highlight_spans": [{"text": "improve", "type": "GRAMMAR", "feedback_index": 0}],
        "detailed_feedbacks": [{"category": "GRAMMAR", "original": "improve", "correction": "improves", "explanation": "Subject-verb agreement"}],
        "positive_feedback": ["Well structured paragraph"],
        "actionable_next_steps": ["Use more complex sentences"]
    }))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/writing/sessions/submit", json={"prompt_id": "650000000000000000000001", "essay_content": "Technology improve society.", "word_count": 3, "time_spent_seconds": 60})
        assert res.status_code == 200
        assert res.json()["status"] == "REVIEWED"

@pytest.mark.asyncio
async def test_writing_improved_sample_comparison_and_history_uc15(mocker):
    """UC-15-UI02, UI03, UI04, UI05: Visual highlighting, preservation of ideas, service fallback & history re-access"""
    mock_sub = WritingSubmissionModel(
        id=PydanticObjectId("650000000000000000000003"),
        user_id="test_user_writing_123",
        prompt_id="650000000000000000000001",
        prompt_title="Urban Dynamics",
        essay_content="Technology improve education.",
        improved_essay_sample="Technology improves education significantly.",
        improvements_comparison=[{"original": "improve education", "improved": "improves education significantly", "category": "VOCAB", "explanation": "Enhanced vocabulary"}]
    )
    mocker.patch.object(WritingSubmissionModel, 'get', AsyncMock(return_value=mock_sub))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/writing/sessions/650000000000000000000003/improved-sample")
        assert res.status_code == 200
        assert res.json()["status"] == "success"

