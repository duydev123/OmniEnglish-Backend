from fastapi import APIRouter, status, Depends
from ..User.user_service import UserService
from ..User.user_dto import (
    LoginRequest,
    RegisterRequest,
    SocialLoginRequest,
    UserProfileResponse,
)
from ..User.user_util import UserUtil

router = APIRouter()
user_service = UserService()

@router.post("/signin", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
@router.post("/login", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def login_user(payload: LoginRequest):
    return await user_service.login(payload)

@router.post("/signup", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest):
    return await user_service.register(payload)

@router.get("/me", response_model=UserProfileResponse)
@router.get("/auth", response_model=UserProfileResponse)
async def get_me(current_user: dict = Depends(UserUtil.Protect)):
    return await user_service.get_profile(current_user)

@router.post("/google", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def google_auth(payload: SocialLoginRequest):
    payload.provider = "google"
    return await user_service.social_login(payload)

@router.post("/facebook", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def facebook_auth(payload: SocialLoginRequest):
    payload.provider = "facebook"
    return await user_service.social_login(payload)