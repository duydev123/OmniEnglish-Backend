from fastapi import APIRouter, status, Depends
from .user_service import UserService
from .user_dto import (
    LoginRequest,
    RegisterRequest,
    SocialLoginRequest,
    UserProfileResponse,
    ChangePasswordRequest,
    UpdateProfileRequest,
    SendOTPRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
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

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    dto: ChangePasswordRequest,
    current_user: dict = Depends(UserUtil.Protect)
):
    return await user_service.change_password(current_user, dto)

@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    dto: UpdateProfileRequest,
    current_user: dict = Depends(UserUtil.Protect)
):
    return await user_service.update_profile(current_user, dto)

@router.post("/forgot-password/send-otp", status_code=status.HTTP_200_OK)
async def send_forgot_otp(dto: SendOTPRequest):
    return await user_service.send_forgot_otp(dto)

@router.post("/forgot-password/verify-otp", status_code=status.HTTP_200_OK)
async def verify_forgot_otp(dto: VerifyOTPRequest):
    return await user_service.verify_forgot_otp(dto)

@router.post("/forgot-password/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_with_otp(dto: ResetPasswordRequest):
    return await user_service.reset_password_with_otp(dto)

@router.post("/check-in", status_code=status.HTTP_200_OK)
@router.post("/daily-checkin", status_code=status.HTTP_200_OK)
async def daily_checkin(current_user: dict = Depends(UserUtil.Protect)):
    return await user_service.daily_checkin(current_user)

@router.get("/activity-logs", status_code=status.HTTP_200_OK)
async def get_activity_logs(current_user: dict = Depends(UserUtil.Protect)):
    return await user_service.get_activity_logs(current_user)
