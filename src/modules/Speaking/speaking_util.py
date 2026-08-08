# src/modules/Speaking/speaking_util.py
from fastapi import UploadFile
from typing import Optional, Dict, Any

class SpeakingUtil:
    # ==========================================
    # 1. NHÓM XỬ LÝ FILE ÂM THANH & LƯU TRỮ (AUDIO & CLOUD)
    # ==========================================
    
    @staticmethod
    async def validate_audio_file(audio_file: UploadFile) -> bool:
        """
        Kiểm tra file upload có hợp lệ không (định dạng .wav, .webm, .m4a, dung lượng max <= 10MB...).
        Throw HTTPException(400) nếu file không hợp lệ.
        """
        pass

    @staticmethod
    async def upload_audio_to_cloud(audio_file: UploadFile, folder: str = "speaking_audios") -> str:
        """
        Upload file âm thanh lên Đám mây (AWS S3, Cloudflare R2 hoặc Cloudinary).
        Trả về: audio_url (str) công khai để lưu vào database.
        """
        pass

    @staticmethod
    async def convert_audio_format(audio_bytes: bytes, target_format: str = "wav") -> bytes:
        """
        (Tuỳ chọn) Chuyển đổi file .webm/.m4a từ trình duyệt sang .wav chuẩn bằng pydub/ffmpeg
        để tối ưu độ chính xác cho mô hình Speech-to-Text AI.
        """
        pass

    # ==========================================
    # 2. NHÓM TRÍ TUỆ NHÂN TẠO (SPEECH-TO-TEXT)
    # ==========================================

    @staticmethod
    async def transcribe_audio_to_text(audio_file_or_url: str | bytes) -> str:
        """
        Gọi dịch vụ AI Speech-to-Text (Whisper API / Deepgram / AssemblyAI).
        Input: Đường dẫn URL hoặc raw bytes âm thanh.
        Output: Đoạn văn bản (user_transcript) người dùng đã nói.
        """
        pass

    @staticmethod
    async def quick_assess_segment(transcript: str, prompt_text: str) -> Dict[str, Any]:
        """
        (Tuỳ chọn) Đánh giá nhanh câu trả lời vừa thu âm (đếm số từ, độ dài câu,
        nhận diện từ vựng tốt) để phản hồi realtime cho frontend ngay sau khi bấm Stop Record.
        Trả về dict chứa: segment_score, realtime_feedback.
        """
        pass

    # ==========================================
    # 3. NHÓM THAO TÁC CƠ SỞ DỮ LIỆU (DATABASE & SESSION)
    # ==========================================

    @staticmethod
    async def get_valid_session(session_id: str, user_id: str):
        """
        Query và validate UserSpeakingTestSessionModel.
        Kiểm tra session có tồn tại, thuộc về user_id và đang có status == "IN_PROGRESS" hay không.
        Throw HTTPException(404/403) nếu không hợp lệ.
        """
        pass

    @staticmethod
    async def update_session_question_detail(
        session_id: str,
        prompt_id: str,
        question_text: str,
        user_transcript: str,
        user_audio_url: str
    ) -> bool:
        """
        Cập nhật hoặc thêm mới 1 phần tử QuestionDetailItem vào mảng `questions_detail`
        trong UserSpeakingTestSessionModel.
        """
        pass