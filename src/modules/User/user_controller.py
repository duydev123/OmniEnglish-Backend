from fastapi import APIRouter, status, Depends
from .user_service import UserService
from .user_dto import (
    LoginRequest,
    RegisterRequest,
    SocialLoginRequest,
    UserProfileResponse,
)
from .user_util import UserUtil

router = APIRouter()
user_service = UserService()

@router.post("/signin", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
@router.post("/login", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def sign_in(dto: LoginRequest):
    return await user_service.login(dto)

@router.post("/signup", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(dto: RegisterRequest):
    return await user_service.register(dto)

@router.get("/auth", response_model=UserProfileResponse)
async def check_auth(current_user: dict = Depends(UserUtil.Protect)):
    return await user_service.get_profile(current_user)

@router.post("/google-login", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def google_login(dto: SocialLoginRequest):
    dto.provider = "google"
    return await user_service.social_login(dto)

@router.post("/facebook-login", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def facebook_login(dto: SocialLoginRequest):
    dto.provider = "facebook"
    return await user_service.social_login(dto)