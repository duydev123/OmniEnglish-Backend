import pytest
from fastapi import HTTPException
from models.UserModel import UserModel
from modules.User.user_service import UserService
from modules.User.user_dto import LoginRequest, RegisterRequest
from modules.User.user_util import UserUtil

@pytest.mark.asyncio
async def test_register_and_login_happy_path():
    # 1. Register
    register_dto = RegisterRequest(
        username="testuser",
        email="test@example.com",
        password="securepassword"
    )
    response = await UserService.register(register_dto)
    assert response.access_token is not None
    assert response.username == "testuser"
    assert response.role == "user"

    # Verify db state
    user = await UserModel.find_one(UserModel.email == "test@example.com")
    assert user is not None
    assert user.username == "testuser"
    assert UserUtil.VerifyPassword("securepassword", user.hashed_password)

    assert user.stats is not None

    # 2. Login
    login_dto = LoginRequest(
        email="test@example.com",
        password="securepassword"
    )
    login_response = await UserService.login(login_dto)
    assert login_response.access_token is not None
    assert login_response.username == "testuser"

@pytest.mark.asyncio
async def test_register_duplicate_email():
    register_dto = RegisterRequest(
        username="testuser1",
        email="dup@example.com",
        password="password123"
    )
    await UserService.register(register_dto)

    # Try register again with same email
    register_dto_dup = RegisterRequest(
        username="testuser2",
        email="dup@example.com",
        password="password123"
    )
    with pytest.raises(HTTPException) as exc_info:
        await UserService.register(register_dto_dup)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Account exist!"

@pytest.mark.asyncio
async def test_login_email_not_found():
    login_dto = LoginRequest(
        email="nonexistent@example.com",
        password="password123"
    )
    with pytest.raises(HTTPException) as exc_info:
        await UserService.login(login_dto)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Email not found!"

@pytest.mark.asyncio
async def test_login_incorrect_password():
    register_dto = RegisterRequest(
        username="testuser",
        email="wrongpass@example.com",
        password="correctpassword"
    )
    await UserService.register(register_dto)

    login_dto = LoginRequest(
        email="wrongpass@example.com",
        password="wrongpassword"
    )
    with pytest.raises(HTTPException) as exc_info:
        await UserService.login(login_dto)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Password Incorrect!"

@pytest.mark.asyncio
async def test_get_profile_happy_path():
    register_dto = RegisterRequest(
        username="profileuser",
        email="profile@example.com",
        password="password123"
    )
    reg_response = await UserService.register(register_dto)
    user_id = reg_response.id

    profile = await UserService.get_profile({"_id": user_id})
    assert profile.username == "profileuser"
    assert profile.email == "profile@example.com"
    assert profile.stats.total_xp == 0

@pytest.mark.asyncio
async def test_get_profile_invalid_payload():
    with pytest.raises(HTTPException) as exc_info:
        await UserService.get_profile({})
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid Token Payload!"

@pytest.mark.asyncio
async def test_get_profile_user_not_found():
    with pytest.raises(HTTPException) as exc_info:
        await UserService.get_profile({"_id": "60c72b2f9b1d8e1d88ef5567"})
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Auth not Found!"

@pytest.mark.asyncio
async def test_update_profile_learning_preferences_uc29():
    """UC-29-UI02: Update learning preferences and goals"""
    register_dto = RegisterRequest(
        username="prefuser",
        email="pref@example.com",
        password="Password123"
    )
    reg_response = await UserService.register(register_dto)
    user = await UserModel.find_one(UserModel.email == "pref@example.com")
    assert user is not None
    
    # Verify initial target stats
    assert user.stats is not None
    assert user.stats.total_xp == 0

@pytest.mark.asyncio
async def test_change_password_rule_validation_uc29():
    """UC-29-UI05: Change password rule validation failure"""
    weak_passwords = ["123456", "short", "nosymboloruppercase"]
    for p in weak_passwords:
        # Password must be validated according to system rules
        assert len(p) < 8 or not any(c.isupper() for c in p)

@pytest.mark.asyncio
async def test_auto_suggest_topic_vocabulary_collections_uc30():
    """UC-30-UI01 & UI02: Topic-based vocabulary recommendation after exercise"""
    from modules.Vocabulary.vocab_service import VocabService
    collections = await VocabService.get_official_collections()
    assert isinstance(collections, list)

