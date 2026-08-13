import pytest
from unittest.mock import MagicMock
from modules.User.user_util import UserUtil

def test_password_hashing():
    password = "MySuperSecurePassword123"
    hashed = UserUtil.HashPassword(password)
    assert hashed != password
    assert UserUtil.VerifyPassword(password, hashed) is True
    assert UserUtil.VerifyPassword("wrong_password", hashed) is False

def test_jwt_token_flow():
    mock_user = MagicMock()
    mock_user.id = "60c72b2f9b1d8e1d88ef5567"
    mock_user.email = "test@example.com"

    token = UserUtil.CreateToken(mock_user)
    assert isinstance(token, str)

    payload = UserUtil.decode_token(token)
    assert payload is not None
    assert payload["_id"] == "60c72b2f9b1d8e1d88ef5567"
    assert payload["email"] == "test@example.com"

def test_jwt_token_flow_dict_input():
    user_dict = {
        "_id": "60c72b2f9b1d8e1d88ef5567",
        "email": "test@example.com"
    }
    token = UserUtil.CreateToken(user_dict)
    assert isinstance(token, str)

    payload = UserUtil.decode_token(token)
    assert payload is not None
    assert payload["_id"] == "60c72b2f9b1d8e1d88ef5567"
    assert payload["email"] == "test@example.com"

def test_decode_invalid_token():
    assert UserUtil.decode_token("invalid_token_string") is None
