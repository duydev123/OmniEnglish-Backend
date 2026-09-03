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
            reading_progress_pct=getattr(stats, "reading_progress_pct", 0.0),
            listening_progress_pct=getattr(stats, "listening_progress_pct", 0.0),
            speaking_progress_pct=getattr(stats, "speaking_progress_pct", 0.0),
            writing_progress_pct=getattr(stats, "writing_progress_pct", 0.0),
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


async def compute_user_streak(user_id: str) -> int:
    """Calculates exact consecutive activity days ending on today (or yesterday)."""
    logs = await DailyActivityLogModel.find({"user_id": str(user_id)}).to_list()
    if not logs:
        return 0
    active_dates = set(l.date_str for l in logs)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    if today_str in active_dates:
        curr_dt = now
    elif yesterday_str in active_dates:
        curr_dt = now - timedelta(days=1)
    else:
        return 0

    streak = 0
    while True:
        d_str = curr_dt.strftime("%Y-%m-%d")
        if d_str in active_dates:
            streak += 1
            curr_dt -= timedelta(days=1)
        else:
            break

    return streak


async def recalculate_and_save_user_stats(user: UserModel) -> UserStats:
    """Dynamically calculates user average band scores for Reading, Listening, Speaking, Writing and Overall Score."""
    if not user:
        return UserStats()

    user_id_str = str(user.id)
    if user.stats is None:
        user.stats = UserStats()

    # Calculate exact consecutive streak days from DailyActivityLogModel
    user.stats.current_streak_days = await compute_user_streak(user_id_str)

    # 1. Reading Average Band Score & Completion Progress %
    try:
        from models.Reading import ReadingPassageModel, UserReadingSessionModel
        total_reading = await ReadingPassageModel.count()
        reading_sessions = await UserReadingSessionModel.find(
            UserReadingSessionModel.user_id == user_id_str,
            UserReadingSessionModel.status == "COMPLETED"
        ).to_list()
        if reading_sessions:
            reading_scores = [
                (s.score / s.total_questions * 9.0) if getattr(s, "total_questions", 0) > 0 else 0.0
                for s in reading_sessions
            ]
            valid_reading = [s for s in reading_scores if s >= 0]
            if valid_reading:
                user.stats.avg_reading_score = round(sum(valid_reading) / len(valid_reading), 1)
        
        unique_reading_ids = set()
        for s in reading_sessions:
            if hasattr(s, "passage_id") and s.passage_id:
                unique_reading_ids.add(str(s.passage_id.ref.id if hasattr(s.passage_id, "ref") else s.passage_id))
        completed_reading = len(unique_reading_ids) or len(reading_sessions)
        user.stats.reading_progress_pct = round((completed_reading / total_reading * 100), 1) if total_reading > 0 else 0.0
    except Exception as e:
        print(f"Error calculating reading stats: {e}")

    # 2. Listening Average Band Score & Completion Progress % (Comprehension + Dictation)
    try:
        from models.Listening import ListeningPassageModel, UserListeningSessionModel, UserDictationSessionModel
        total_listening = await ListeningPassageModel.count()
        listening_sessions = await UserListeningSessionModel.find(
            UserListeningSessionModel.user_id == user_id_str,
            UserListeningSessionModel.status == "COMPLETED"
        ).to_list()
        dictation_sessions = await UserDictationSessionModel.find(
            UserDictationSessionModel.user_id == user_id_str,
            UserDictationSessionModel.status == "COMPLETED"
        ).to_list()

        listening_scores = []
        for s in listening_sessions:
            if getattr(s, "accuracy_rate", None) is not None:
                listening_scores.append(s.accuracy_rate / 100.0 * 9.0)
        for d in dictation_sessions:
            if getattr(d, "accuracy_rate", None) is not None:
                listening_scores.append(d.accuracy_rate / 100.0 * 9.0)

        if listening_scores:
            user.stats.avg_listening_score = round(sum(listening_scores) / len(listening_scores), 1)

        unique_listening_ids = set()
        for s in listening_sessions:
            if hasattr(s, "passage_id") and s.passage_id:
                unique_listening_ids.add(str(s.passage_id.ref.id if hasattr(s.passage_id, "ref") else s.passage_id))
        for d in dictation_sessions:
            if hasattr(d, "passage_id") and d.passage_id:
                unique_listening_ids.add(str(d.passage_id.ref.id if hasattr(d.passage_id, "ref") else d.passage_id))
        completed_listening = len(unique_listening_ids) or (len(listening_sessions) + len(dictation_sessions))
        user.stats.listening_progress_pct = round((completed_listening / total_listening * 100), 1) if total_listening > 0 else 0.0
    except Exception as e:
        print(f"Error calculating listening stats: {e}")

    # 3. Speaking Average Band Score & Completion Progress %
    try:
        from models.Speaking import SpeakingTopicModel, ShadowingSentenceModel, UserSpeakingTestSessionModel
        total_speaking_items = (await SpeakingTopicModel.count()) + (await ShadowingSentenceModel.count())
        speaking_sessions = await UserSpeakingTestSessionModel.find(
            UserSpeakingTestSessionModel.user_id == user_id_str,
            UserSpeakingTestSessionModel.status == "COMPLETED"
        ).to_list()
        if speaking_sessions:
            speaking_scores = [s.overall_band_score for s in speaking_sessions if getattr(s, "overall_band_score", 0) > 0]
            if speaking_scores:
                user.stats.avg_speaking_score = round(sum(speaking_scores) / len(speaking_scores), 1)

        unique_speaking_ids = set()
        for s in speaking_sessions:
            if hasattr(s, "prompt_id") and s.prompt_id:
                unique_speaking_ids.add(str(s.prompt_id.ref.id if hasattr(s.prompt_id, "ref") else s.prompt_id))
            elif getattr(s, "title", None):
                unique_speaking_ids.add(s.title)
        completed_speaking = len(unique_speaking_ids) or len(speaking_sessions)
        user.stats.speaking_progress_pct = round((completed_speaking / total_speaking_items * 100), 1) if total_speaking_items > 0 else 0.0
    except Exception as e:
        print(f"Error calculating speaking stats: {e}")

    # 4. Writing Average Band Score & Completion Progress %
    try:
        from models.Writing import WritingPromptModel, WritingSubmissionModel
        total_writing = await WritingPromptModel.count()
        writing_submissions = await WritingSubmissionModel.find(
            WritingSubmissionModel.user_id == user_id_str
        ).to_list()
        if writing_submissions:
            valid_writing = [s.overall_score for s in writing_submissions if getattr(s, "overall_score", 0) > 0]
            if valid_writing:
                user.stats.avg_writing_score = round(sum(valid_writing) / len(valid_writing), 1)

        unique_writing_ids = set()
        for s in writing_submissions:
            if hasattr(s, "prompt_id") and s.prompt_id:
                unique_writing_ids.add(str(s.prompt_id.ref.id if hasattr(s.prompt_id, "ref") else s.prompt_id))
        completed_writing = len(unique_writing_ids) or len(writing_submissions)
        user.stats.writing_progress_pct = round((completed_writing / total_writing * 100), 1) if total_writing > 0 else 0.0
    except Exception as e:
        print(f"Error calculating writing stats: {e}")

    # 5. Vocabulary Words Learned count
    try:
        from models.VocabularyCollection import UserWordStatusModel
        user_words = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id_str
        ).to_list()
        unique_words = set(w.word for w in user_words if getattr(w, "word", None))
        user.stats.total_words_learned = len(unique_words)
    except Exception as e:
        print(f"Error calculating vocabulary stats: {e}")

    # 6. Overall Average Score across active non-zero module scores
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
    except Exception as e:
        print(f"Error saving user stats: {e}")

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

        if user.status and user.status.lower() == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị tạm khóa bởi Quản trị viên! Vui lòng liên hệ bộ phận hỗ trợ."
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

        if user.status and user.status.lower() == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị tạm khóa bởi Quản trị viên!"
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
            if user.status and user.status.lower() == "suspended":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tài khoản của bạn đã bị tạm khóa bởi Quản trị viên! Vui lòng liên hệ bộ phận hỗ trợ."
                )
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
    async def record_activity(user_id: str, xp: int = 10):
        if not user_id:
            return
        user = await _get_user_by_id(user_id)
        if not user:
            return

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        existing_log = await DailyActivityLogModel.find_one({
            "user_id": str(user.id),
            "date_str": today_str
        })

        if not existing_log:
            new_log = DailyActivityLogModel(
                user_id=str(user.id),
                date_str=today_str,
                activities_count=1,
                xp_earned=xp
            )
            await new_log.insert()

            user.stats.current_streak_days = await compute_user_streak(str(user.id))
            user.stats.total_xp = (user.stats.total_xp or 0) + xp
            user.last_login_at = now
            await user.save()
        else:
            existing_log.activities_count += 1
            existing_log.xp_earned = (existing_log.xp_earned or 0) + xp
            await existing_log.save()

            user.stats.current_streak_days = await compute_user_streak(str(user.id))
            user.stats.total_xp = (user.stats.total_xp or 0) + xp
            user.last_login_at = now
            await user.save()

    @staticmethod
    async def daily_checkin(current_user: dict) -> dict:
        user_id = current_user.get("_id") or current_user.get("user_id") or current_user.get("id")
        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        existing_log = await DailyActivityLogModel.find_one({
            "user_id": str(user.id),
            "date_str": today_str
        })

        today_checked_in = True
        if not existing_log:
            new_log = DailyActivityLogModel(
                user_id=str(user.id),
                date_str=today_str,
                activities_count=1,
                xp_earned=10
            )
            await new_log.insert()

            user.stats.current_streak_days = await compute_user_streak(str(user.id))
            user.last_login_at = now
            await user.save()
        else:
            existing_log.activities_count += 1
            await existing_log.save()
            user.stats.current_streak_days = await compute_user_streak(str(user.id))
            user.last_login_at = now
            await user.save()

        # Fetch active dates
        logs = await DailyActivityLogModel.find({
            "user_id": str(user.id)
        }).to_list()
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

        logs = await DailyActivityLogModel.find({
            "user_id": str(user_id)
        }).sort("+date_str").to_list()

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