import pytest
from models.User import UserModel

@pytest.mark.asyncio
async def test_auth_flow_integration(client):
    # 1. Sign up
    signup_payload = {
        "username": "api_user",
        "email": "api_user@example.com",
        "password": "api_password"
    }
    response = await client.post("/api/v1/users/signup", json=signup_payload)
    assert response.status_code == 201
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["username"] == "api_user"

    token = res_data["access_token"]

    # 2. Check Auth (success)
    headers = {"Authorization": f"Bearer {token}"}
    auth_response = await client.get("/api/v1/users/auth", headers=headers)
    assert auth_response.status_code == 200
    profile_data = auth_response.json()
    assert profile_data["email"] == "api_user@example.com"
    assert profile_data["username"] == "api_user"

    # 3. Check Auth (unauthorized - missing header)
    unauth_response = await client.get("/api/v1/users/auth")
    assert unauth_response.status_code == 401  # HTTPBearer returns 401/403 on missing credentials depending on settings


    # 4. Check Auth (unauthorized - invalid token)
    unauth_response_2 = await client.get("/api/v1/users/auth", headers={"Authorization": "Bearer invalid_token"})
    assert unauth_response_2.status_code == 401
    assert unauth_response_2.json()["message"] == "Token không hợp lệ hoặc đã hết hạn!"


    # 5. Sign in
    signin_payload = {
        "email": "api_user@example.com",
        "password": "api_password"
    }
    signin_response = await client.post("/api/v1/users/signin", json=signin_payload)
    assert signin_response.status_code == 200
    signin_data = signin_response.json()
    assert "access_token" in signin_data
    assert signin_data["username"] == "api_user"
