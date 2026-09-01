import pytest
from unittest.mock import AsyncMock, MagicMock
from beanie import PydanticObjectId
from httpx import AsyncClient, ASGITransport
from main import app
from modules.Admin.admin_service import AdminService
from modules.Admin.admin_dto import ContentSetDTO, AdminUserDTO, AdminCMSStatsDTO

@pytest.mark.asyncio
async def test_get_cms_content_sets(mocker):
    mock_sets = [
        ContentSetDTO(
            id="cs_1",
            title="IELTS Reading Practice Set 1",
            category="READING (20 CÂU HỎI)",
            badge="READING (20 Qs)",
            itemsCount=20,
            itemUnit="Questions",
            status="Published",
            updatedAt="2026-09-01",
            type="reading"
        )
    ]
    mocker.patch.object(AdminService, 'get_cms_content_sets', AsyncMock(return_value=mock_sets))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/admin/cms/content-sets")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "IELTS Reading Practice Set 1"

@pytest.mark.asyncio
async def test_create_content_set(mocker):
    mock_created = ContentSetDTO(
        id="cs_2",
        title="Speaking Part 2 Topics",
        category="SPEAKING (5 CÂU HỎI)",
        badge="SPEAKING (5 Qs)",
        itemsCount=5,
        itemUnit="Questions",
        status="Published",
        updatedAt="2026-09-01",
        type="speaking"
    )
    mocker.patch.object(AdminService, 'create_content_set', AsyncMock(return_value=mock_created))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "title": "Speaking Part 2 Topics",
            "category": "SPEAKING (5 CÂU HỎI)",
            "itemsCount": 5,
            "status": "Published",
            "type": "speaking"
        }
        res = await ac.post("/api/v1/admin/cms/content-sets", json=payload)
        assert res.status_code == 200
        assert res.json()["id"] == "cs_2"

@pytest.mark.asyncio
async def test_update_content_set(mocker):
    mock_updated = ContentSetDTO(
        id="cs_1",
        title="Updated Title",
        category="READING",
        badge="READING",
        itemsCount=20,
        itemUnit="Questions",
        status="Draft",
        updatedAt="2026-09-01",
        type="reading"
    )
    mocker.patch.object(AdminService, 'update_content_set', AsyncMock(return_value=mock_updated))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put("/api/v1/admin/cms/content-sets/cs_1", json={"title": "Updated Title", "status": "Draft"})
        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_delete_content_set(mocker):
    mocker.patch.object(AdminService, 'delete_content_set', AsyncMock(return_value={"status": "deleted", "id": "cs_1"}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete("/api/v1/admin/cms/content-sets/cs_1")
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"

@pytest.mark.asyncio
async def test_get_cms_stats(mocker):
    mock_stats = AdminCMSStatsDTO(
        totalVocabItems=1200,
        publishedSets=10,
        draftsPending=2
    )
    mocker.patch.object(AdminService, 'get_cms_stats', AsyncMock(return_value=mock_stats))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/admin/cms/stats")
        assert res.status_code == 200
        assert res.json()["totalVocabItems"] == 1200

@pytest.mark.asyncio
async def test_get_admin_users(mocker):
    mock_users = [
        AdminUserDTO(
            id="u_1",
            username="adminuser",
            email="admin@example.com",
            role="Admin",
            proficiency_level="C1",
            proficiency_label="Advanced",
            status="Active",
            joined_date="2026-01-01"
        )
    ]
    mocker.patch.object(AdminService, 'get_users', AsyncMock(return_value=mock_users))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/admin/users")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["role"] == "Admin"

@pytest.mark.asyncio
async def test_create_admin_user(mocker):
    mock_new_user = AdminUserDTO(
        id="u_2",
        username="newstudent",
        email="student@example.com",
        role="Student",
        proficiency_level="B2",
        proficiency_label="Upper Int.",
        status="Active",
        joined_date="2026-09-01"
    )
    mocker.patch.object(AdminService, 'create_user', AsyncMock(return_value=mock_new_user))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "username": "newstudent",
            "email": "student@example.com",
            "password": "Password123!",
            "role": "Student",
            "status": "Active"
        }
        res = await ac.post("/api/v1/admin/users", json=payload)
        assert res.status_code == 200
        assert res.json()["username"] == "newstudent"

@pytest.mark.asyncio
async def test_update_admin_user(mocker):
    mock_updated_user = AdminUserDTO(
        id="u_2",
        username="newstudent",
        email="student@example.com",
        role="Admin",
        proficiency_level="C1",
        proficiency_label="Advanced",
        status="Active",
        joined_date="2026-09-01"
    )
    mocker.patch.object(AdminService, 'update_user', AsyncMock(return_value=mock_updated_user))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put("/api/v1/admin/users/u_2", json={"role": "Admin", "proficiency_level": "C1"})
        assert res.status_code == 200
        assert res.json()["role"] == "Admin"

@pytest.mark.asyncio
async def test_delete_admin_user(mocker):
    mocker.patch.object(AdminService, 'delete_user', AsyncMock(return_value={"status": "deleted", "id": "u_2"}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete("/api/v1/admin/users/u_2")
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"
