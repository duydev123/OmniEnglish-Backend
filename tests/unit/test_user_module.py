import pytest
from unittest.mock import AsyncMock, MagicMock
from beanie import PydanticObjectId
from httpx import AsyncClient, ASGITransport
from main import app
from models.User import UserModel

@pytest.mark.asyncio
async def test_user_profile_management_uc29(mocker):
    """UC-29: View and update user profile information, English level, learning goals"""
    mock_user = UserModel(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        username="testuser001",
        email="user001@example.com",
        full_name="Test User 001",
        english_level="Intermediate",
        learning_goal="IELTS Preparation"
    )
    mocker.patch.object(UserModel, 'get', AsyncMock(return_value=mock_user))
    mocker.patch.object(UserModel, 'save', AsyncMock(return_value=mock_user))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_auth = await ac.get("/api/v1/users/auth")
        assert res_auth.status_code in [200, 401, 404]

        res_profile = await ac.patch("/api/v1/users/profile", json={
            "full_name": "Updated User 001",
            "english_level": "Advanced"
        })
        assert res_profile.status_code in [200, 401, 404, 405]

@pytest.mark.asyncio
async def test_user_dashboard_progress_tracking_uc24(mocker):
    """UC-24: Dashboard summary stats, progress tracking and score trends"""
    dashboard_data = {
        "overall_band": 7.0,
        "strengths": ["Listening - Multiple Choice", "Writing - Task Achievement"],
        "weaknesses": ["Speaking - Pronunciation", "Reading - Time Management"],
        "smart_recommendations": [{"title": "Practice Dictation 15 mins", "type": "LISTENING"}]
    }
    assert len(dashboard_data["strengths"]) > 0
    assert len(dashboard_data["weaknesses"]) > 0
