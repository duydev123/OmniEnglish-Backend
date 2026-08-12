from fastapi import HTTPException, status
from models.UserModel import UserModel, UserStatsModel, UserSettings
from .user_dto import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserSettingsResponse,
    UserStatsResponse,
)
from .user_util import UserUtil


class UserService:
    @staticmethod
    async def login(data: LoginRequest) -> TokenResponse:
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

        # 3. Tạo Token và trả về TokenResponse
        token = UserUtil.CreateToken(user)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=str(user.id),
            username=user.username,
            role=user.role or "user"
        )
    @staticmethod
    async def register(data: RegisterRequest) -> TokenResponse:
        # 1. Kiểm tra tài khoản đã tồn tại chưa
        existing_user = await UserModel.find_one(UserModel.email == data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account exist!"
            )

        # 2. Hash mật khẩu
        hash_pass = UserUtil.HashPassword(data.password)

        # 3. Tạo UserModel mới trong Database
        new_user = UserModel(
            username=data.username,
            email=data.email,
            hashed_password=hash_pass,
            role="user",
            avatar=""
        )
        await new_user.insert()

        # 4. Khởi tạo bản ghi UserStatsModel cho user mới
        user_stats = UserStatsModel(user_id=str(new_user.id))
        await user_stats.insert()

        # 5. Tạo token và trả về
        token = UserUtil.CreateToken(new_user)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=str(new_user.id),
            username=new_user.username,
            role=new_user.role
        )

    @staticmethod
    async def get_profile(current_user: dict) -> UserProfileResponse:
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

        # Lấy hoặc tạo thông số thống kê (UserStatsModel)
        stats = await UserStatsModel.find_one(UserStatsModel.user_id == str(user.id))
        if not stats:
            stats = UserStatsModel(user_id=str(user.id))
            await stats.insert()

        # Cài đặt mặc định
        default_settings = UserSettings()

        return UserProfileResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role or "user",
            avatar=user.avatar or "",
            proficiency_level=user.proficiency_level or "B1",
            status=user.status or "Active",
            settings=UserSettingsResponse(
                focus_areas=default_settings.focus_areas,
                daily_word_target=default_settings.daily_word_target,
                learning_mode=default_settings.learning_mode,
                weekend_mastery=default_settings.weekend_mastery,
                base_language=default_settings.base_language,
                notifications_enabled=default_settings.notifications_enabled,
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

    # --- Alias giữ tương thích với tên hàm cũ ---
    SignIn = login
    signup = register
    authCheck = get_profile