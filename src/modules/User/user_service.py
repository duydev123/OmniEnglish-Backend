import random
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from typing import Optional
from beanie import PydanticObjectId
from models.User import UserModel, UserSettings, UserStats, PasswordResetOTPModel, DailyActivityLogModel
from core.email_service import EmailService
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
    SendOTPRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
)
from .user_util import UserUtil


def build_user_profile_response(user: UserModel, token: Optional[str] = None) -> UserProfileResponse:
    settings = user.settings or UserSettings()
    stats = user.stats or UserStats()
    created_at_str = user.created_at.strftime("%B %Y") if getattr(user, "created_at", None) else datetime.now(timezone.utc).strftime("%B %Y")
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
            overall_score=getattr(stats, "overall_score", 0.0),
        ),
    )


async def _get_user_by_id(user_id: str) -> Optional[UserModel]:
    if not user_id:
        return None
    try:
        user = await UserModel.get(PydanticObjectId(user_id))
        if user:
            return user
    except Exception:
        pass
    try:
        return await UserModel.get(user_id)
    except Exception:
        return None


async def recalculate_and_save_user_stats(user: UserModel) -> UserStats:
    """Dynamically calculates user average band scores for Reading, Listening, Speaking, Writing and Overall Score."""
    if not user:
        return UserStats()

    user_id_str = str(user.id)
    if user.stats is None:
        user.stats = UserStats()

    # 1. Reading Average Band Score (1.0 - 9.0)
    try:
        from models.Reading import UserReadingSessionModel
        reading_sessions = await UserReadingSessionModel.find(
            UserReadingSessionModel.user_id == user_id_str,
            UserReadingSessionModel.status == "COMPLETED"
        ).to_list()
        if reading_sessions:
            reading_scores = [
                (s.score / s.total_questions * 9.0) if s.total_questions > 0 else 0.0
                for s in reading_sessions
            ]
            user.stats.avg_reading_score = round(sum(reading_scores) / len(reading_scores), 1)
        else:
            user.stats.avg_reading_score = 0.0
    except Exception:
        pass

    # 2. Listening Average Band Score (1.0 - 9.0)
    try:
        from models.Listening import UserListeningSessionModel
        listening_sessions = await UserListeningSessionModel.find(
            UserListeningSessionModel.user_id == user_id_str,
            UserListeningSessionModel.status == "COMPLETED"
        ).to_list()
        if listening_sessions:
            listening_scores = [
                (s.accuracy_rate / 100.0 * 9.0) for s in listening_sessions
            ]
            user.stats.avg_listening_score = round(sum(listening_scores) / len(listening_scores), 1)
        else:
            user.stats.avg_listening_score = 0.0
    except Exception:
        pass

    # 3. Speaking Average Band Score (1.0 - 9.0)
    try:
        from models.Speaking import UserSpeakingTestSessionModel
        speaking_sessions = await UserSpeakingTestSessionModel.find(
            UserSpeakingTestSessionModel.user_id == user_id_str,
            UserSpeakingTestSessionModel.status == "COMPLETED"
        ).to_list()
        if speaking_sessions:
            speaking_scores = [s.overall_band_score for s in speaking_sessions if s.overall_band_score > 0]
            if speaking_scores:
                user.stats.avg_speaking_score = round(sum(speaking_scores) / len(speaking_scores), 1)
            else:
                user.stats.avg_speaking_score = 0.0
        else:
            user.stats.avg_speaking_score = 0.0
    except Exception:
        pass

    # 4. Writing Average Band Score (1.0 - 9.0)
    try:
        from models.Writing import WritingSubmissionModel
        writing_submissions = await WritingSubmissionModel.find(
            WritingSubmissionModel.user_id == user_id_str
        ).to_list()
        if writing_submissions:
            valid_writing = [s.overall_score for s in writing_submissions if s.overall_score > 0]
            if valid_writing:
                user.stats.avg_writing_score = round(sum(valid_writing) / len(valid_writing), 1)
            else:
                user.stats.avg_writing_score = 0.0
        else:
            user.stats.avg_writing_score = 0.0
    except Exception:
        pass

    # 5. Overall Average Score across active non-zero module scores
    active_scores = [
        s for s in [
            user.stats.avg_reading_score,
            user.stats.avg_listening_score,
            user.stats.avg_speaking_score,
            user.stats.avg_writing_score
        ] if s > 0
    ]
    if active_scores:
        user.stats.overall_score = round(sum(active_scores) / len(active_scores), 1)
    else:
        user.stats.overall_score = 0.0

    try:
        await user.save()
    except Exception:
        pass

    return user.stats


class UserService:
    @staticmethod
    async def login(data: LoginRequest) -> UserProfileResponse:
        user = await UserModel.find_one(UserModel.email == data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found!"
            )

        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản này được đăng ký qua Google/Facebook. Vui lòng chọn Đăng nhập bằng Google hoặc dùng tính năng Quên mật khẩu để tạo mật khẩu!"
            )

        if not UserUtil.VerifyPassword(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mật khẩu không chính xác!"
            )

        token = UserUtil.CreateToken(user)
        return build_user_profile_response(user, token=token)

    @staticmethod
    async def register(data: RegisterRequest) -> UserProfileResponse:
        existing_user = await UserModel.find_one(UserModel.email == data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account exist!"
            )

        hash_pass = UserUtil.HashPassword(data.password)
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

        token = UserUtil.CreateToken(new_user)
        return build_user_profile_response(new_user, token=token)

    @staticmethod
    async def get_profile(current_user: dict) -> UserProfileResponse:
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Token Payload!"
            )

        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth not Found!"
            )

        await recalculate_and_save_user_stats(user)
        return build_user_profile_response(user)

    @staticmethod
    async def social_login(data: SocialLoginRequest) -> UserProfileResponse:
        user = await UserModel.find_one(UserModel.email == data.email)
        
        if not user:
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
            if data.avatar and not user.avatar:
                user.avatar = data.avatar
                await user.save()

        token = UserUtil.CreateToken(user)
        return build_user_profile_response(user, token=token)

    @staticmethod
    async def update_profile(current_user: dict, dto: UpdateProfileRequest) -> UserProfileResponse:
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token Payload!")

        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if dto.avatar is not None:
            user.avatar = dto.avatar
        if dto.username is not None and len(dto.username.strip()) >= 3:
            user.username = dto.username.strip()
        if dto.proficiency_level is not None:
            user.proficiency_level = dto.proficiency_level

        if user.settings is None:
            user.settings = UserSettings()

        if dto.settings:
            if dto.settings.focus_areas is not None:
                user.settings.focus_areas = dto.settings.focus_areas
            if dto.settings.daily_word_target is not None:
                user.settings.daily_word_target = dto.settings.daily_word_target
            if dto.settings.learning_mode is not None:
                user.settings.learning_mode = dto.settings.learning_mode
            if dto.settings.weekend_mastery is not None:
                user.settings.weekend_mastery = dto.settings.weekend_mastery
            if dto.settings.base_language is not None:
                user.settings.base_language = dto.settings.base_language
            if dto.settings.notifications_enabled is not None:
                user.settings.notifications_enabled = dto.settings.notifications_enabled

        if dto.daily_word_target is not None:
            user.settings.daily_word_target = dto.daily_word_target
        if dto.learning_mode is not None:
            user.settings.learning_mode = dto.learning_mode
        if dto.weekend_mastery is not None:
            user.settings.weekend_mastery = dto.weekend_mastery
        if dto.base_language is not None:
            user.settings.base_language = dto.base_language
        if dto.notifications_enabled is not None:
            user.settings.notifications_enabled = dto.notifications_enabled

        await user.save()
        return build_user_profile_response(user)

    @staticmethod
    async def change_password(current_user: dict, dto: ChangePasswordRequest):
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token Payload!")

        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")

        if not user.hashed_password or not UserUtil.VerifyPassword(dto.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu cũ không chính xác!")

        user.hashed_password = UserUtil.HashPassword(dto.new_password)
        await user.save()
        return {"status": "success", "message": "Đổi mật khẩu thành công!"}

    @staticmethod
    async def send_forgot_otp(data: SendOTPRequest):
        user = await UserModel.find_one(UserModel.email == data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email không tồn tại trong hệ thống!"
            )

        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        otp_doc = PasswordResetOTPModel(
            email=data.email,
            otp_code=otp_code,
            expires_at=expires_at,
            is_used=False
        )
        await otp_doc.insert()

        EmailService.send_otp_email(to_email=data.email, otp_code=otp_code, username=user.username)
        return {
            "status": "success",
            "message": "Mã xác nhận OTP đã được gửi tới email của bạn. Vui lòng kiểm tra hộp thư!"
        }

    @staticmethod
    async def verify_forgot_otp(data: VerifyOTPRequest):
        otp_doc = await PasswordResetOTPModel.find_one(
            PasswordResetOTPModel.email == data.email,
            PasswordResetOTPModel.otp_code == data.otp_code,
            PasswordResetOTPModel.is_used == False
        )
        if not otp_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã OTP không chính xác!"
            )

        now = datetime.now(timezone.utc)
        exp = otp_doc.expires_at.replace(tzinfo=timezone.utc) if otp_doc.expires_at.tzinfo is None else otp_doc.expires_at
        if now > exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã OTP đã hết hạn! Vui lòng yêu cầu mã mới."
            )

        return {"status": "success", "message": "Mã OTP hợp lệ!"}

    @staticmethod
    async def reset_password_with_otp(data: ResetPasswordRequest):
        otp_doc = await PasswordResetOTPModel.find_one(
            PasswordResetOTPModel.email == data.email,
            PasswordResetOTPModel.otp_code == data.otp_code,
            PasswordResetOTPModel.is_used == False
        )
        if not otp_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã OTP không hợp lệ hoặc đã được sử dụng!"
            )

        now = datetime.now(timezone.utc)
        exp = otp_doc.expires_at.replace(tzinfo=timezone.utc) if otp_doc.expires_at.tzinfo is None else otp_doc.expires_at
        if now > exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã OTP đã hết hạn! Vui lòng yêu cầu mã mới."
            )

        user = await UserModel.find_one(UserModel.email == data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tài khoản không tồn tại!"
            )

        user.hashed_password = UserUtil.HashPassword(data.new_password)
        await user.save()

        otp_doc.is_used = True
        await otp_doc.save()

        return {"status": "success", "message": "Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay."}

    @staticmethod
    async def daily_checkin(current_user: dict) -> dict:
        user_id = current_user.get("_id") or current_user.get("user_id") or current_user.get("id")
        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        existing_log = await DailyActivityLogModel.find_one(
            DailyActivityLogModel.user_id == str(user.id),
            DailyActivityLogModel.date_str == today_str
        )

        today_checked_in = True
        if not existing_log:
            new_log = DailyActivityLogModel(
                user_id=str(user.id),
                date_str=today_str,
                activities_count=1,
                xp_earned=10
            )
            await new_log.insert()

            # Update Streak: check if user had activity yesterday
            yesterday_log = await DailyActivityLogModel.find_one(
                DailyActivityLogModel.user_id == str(user.id),
                DailyActivityLogModel.date_str == yesterday_str
            )

            current_streak = user.stats.current_streak_days or 0
            if yesterday_log:
                user.stats.current_streak_days = current_streak + 1
            else:
                user.stats.current_streak_days = 1
            
            user.last_login_at = now
            await user.save()
        else:
            existing_log.activities_count += 1
            await existing_log.save()
            user.last_login_at = now
            await user.save()

        # Fetch active dates
        logs = await DailyActivityLogModel.find(
            DailyActivityLogModel.user_id == str(user.id)
        ).to_list()
        activity_dates = [l.date_str for l in logs]

        return {
            "status": "success",
            "message": "Đã ghi nhận đăng nhập / hoạt động hôm nay thành công!",
            "today_checked_in": today_checked_in,
            "streak_days": user.stats.current_streak_days,
            "activity_dates": activity_dates,
            "user": build_user_profile_response(user)
        }

    @staticmethod
    async def get_activity_logs(current_user: dict) -> dict:
        user_id = current_user.get("_id") or current_user.get("user_id") or current_user.get("id")
        if not user_id:
            return {"data": []}

        logs = await DailyActivityLogModel.find(
            DailyActivityLogModel.user_id == str(user_id)
        ).sort("+date_str").to_list()

        results = [
            {
                "date_str": l.date_str,
                "activities_count": l.activities_count,
                "xp_earned": l.xp_earned
            }
            for l in logs
        ]

        return {"status": "success", "data": results}

    # --- Aliases ---
    SignIn = login
    signup = register
    authCheck = get_profile