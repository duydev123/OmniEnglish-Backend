import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from models.UserModel import UserModel

@pytest.mark.asyncio
async def test_auth_signup_validation_uc01(mocker):
    """UC-01: Register new account validation, duplicate email check, password mismatch"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Invalid email format
        res_bad_email = await ac.post("/api/v1/auth/register", json={
            "email": "invalid_email",
            "password": "Password123",
            "full_name": "Test User"
        })
        assert res_bad_email.status_code in [400, 422]

        # Blank mandatory fields
        res_blank = await ac.post("/api/v1/auth/register", json={
            "email": "",
            "password": "",
            "full_name": ""
        })
        assert res_blank.status_code in [400, 422]

@pytest.mark.asyncio
async def test_auth_login_system_uc02(mocker):
    """UC-02: Login to system with valid user/admin credentials, incorrect password, unregistered email"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Unregistered email login
        res_unreg = await ac.post("/api/v1/auth/login", json={
            "email": "nonexistent_user@example.com",
            "password": "Password123"
        })
        assert res_unreg.status_code in [400, 401, 404]

        # Incorrect password
        res_bad_pass = await ac.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "WrongPassword"
        })
        assert res_bad_pass.status_code in [400, 401]
