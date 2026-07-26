from fastapi import APIRouter
# from ..User.user_dto import (
#     SigninRequest,
#     SignupRequest,
#     SigninResponse,
#     AuthResponse
# )

router = APIRouter()

# @router.post(path="/signup", response_model=AuthResponse)
# async def register_user(payload: SignupRequest):
#     """Đăng ký tài khoản người dùng mới"""
#     pass

# @router.post(path="/signin", response_model=SigninResponse)
# async def login_user(payload: SigninRequest):
#     """Đăng nhập và nhận JWT Token"""
#     pass