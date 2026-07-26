from fastapi import APIRouter, status, Depends
from .user_service import UserService
from .user_dto import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
)
from .user_util import UserUtil

router = APIRouter()
user_service = UserService()

@router.post("/signin", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def sign_in(dto: LoginRequest):
    return await user_service.login(dto)

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(dto: RegisterRequest):
    return await user_service.register(dto)

@router.get("/auth", response_model=UserProfileResponse)
async def check_auth(current_user: dict = Depends(UserUtil.Protect)):
    return await user_service.get_profile(current_user)