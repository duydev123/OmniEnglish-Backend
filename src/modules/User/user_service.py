from fastapi import HTTPException, status
from typing import Optional
from models.UserModel import UserModel, UserSettings, UserStats
from .user_dto import (
    LoginRequest,
    RegisterRequest,
    SocialLoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserSettingsResponse,
    UserStatsResponse,
    ChangePasswordRequest,
    UpdateProfileRequest,
)
from .user_util import UserUtil


def build_user_profile_response(user: UserModel, token: Optional[str] = None) -> UserProfileResponse:
    settings = user.settings or UserSettings()
    stats = user.stats or UserStats()
    created_at_str = user.created_at.strftime("%B %Y") if getattr(user, "created_at", None) else "August 2024"
    return UserProfileResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role or "user",
        avatar=user.avatar or "",
        proficiency_level=user.proficiency_level or "A1",
        status=user.status or "Active",
        token=token,
        access_token=token,
        created_at=created_at_str,
        settings=UserSettingsResponse(
            focus_areas=settings.focus_areas,
            daily_word_target=settings.daily_word_target,
            learning_mode=settings.learning_mode,
            weekend_mastery=settings.weekend_mastery,
            base_language=settings.base_language,
            notifications_enabled=settings.notifications_enabled,
        ),
        stats=UserStatsResponse(
            current_streak_days=stats.current_streak_days,
            total_xp=stats.total_xp,
            weekly_xp=stats.weekly_xp,
            total_words_learned=stats.total_words_learned,
            total_speaking_hours=stats.total_speaking_hours,
            general_english_level=stats.general_english_level,
            business_english_progress=stats.business_english_progress,
            avg_reading_score=stats.avg_reading_score,
            avg_listening_score=stats.avg_listening_score,
            avg_speaking_score=stats.avg_speaking_score,
            avg_writing_score=stats.avg_writing_score,
        ),
    )


class UserService:
    async def login(self, data: LoginRequest) -> UserProfileResponse:
        # 1. Tìm user theo email
        user = await UserModel.find_one(UserModel.email == data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found!"
            )

        # 2. Kiểm tra mật khẩu
        if not user.hashed_password or not UserUtil.VerifyPassword(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password Incorrect!"
            )

        # 3. Tạo Token và trả về UserProfileResponse chứa token
        token = UserUtil.CreateToken(user)
        return build_user_profile_response(user, token=token)

    async def register(self, data: RegisterRequest) -> UserProfileResponse:
        # 1. Kiểm tra tài khoản đã tồn tại chưa
        existing_user = await UserModel.find_one(UserModel.email == data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account exist!"
            )

        # 2. Hash mật khẩu
        hash_pass = UserUtil.HashPassword(data.password)

        # 3. Tạo UserModel mới trong Database (embedded settings & stats)
        new_user = UserModel(
            username=data.username,
            email=data.email,
            hashed_password=hash_pass,
            auth_provider="local",
            role="user",
            avatar="",
            settings=UserSettings(),
            stats=UserStats()
        )
        await new_user.insert()

        # 4. Tạo token và trả về UserProfileResponse chứa token
        token = UserUtil.CreateToken(new_user)
        return build_user_profile_response(new_user, token=token)

    async def get_profile(self, current_user: dict) -> UserProfileResponse:
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Token Payload!"
            )

        user = await UserModel.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth not Found!"
            )

        return build_user_profile_response(user)

    async def social_login(self, data: SocialLoginRequest) -> UserProfileResponse:
        # Tìm user theo email
        user = await UserModel.find_one(UserModel.email == data.email)
        
        if not user:
            # Tạo user mới nếu chưa tồn tại
            username_val = data.name or data.email.split("@")[0]
            user = UserModel(
                username=username_val,
                email=data.email,
                auth_provider=data.provider,
                role="user",
                avatar=data.avatar or "",
                settings=UserSettings(),
                stats=UserStats()
            )
            await user.insert()
        else:
            # Cập nhật avatar nếu có
            if data.avatar and not user.avatar:
                user.avatar = data.avatar
                await user.save()

        token = UserUtil.CreateToken(user)
        return build_user_profile_response(user, token=token)

    # --- Alias giữ tương thích với tên hàm cũ ---
    SignIn = login
    signup = register
    authCheck = get_profile