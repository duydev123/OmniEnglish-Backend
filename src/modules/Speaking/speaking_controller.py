from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from modules.User.user_util import UserUtil

# Import các DTO (Data Transfer Object) - Ông cần bổ sung thêm các schema này bên file speaking_dto.py
from .speaking_dto import (
    SpeakingPromptResponse, 
    SpeakingSegmentSubmitRequest, 
    SpeakingSegmentSubmitResponse,
    SpeakingSubmitResponse,
    # Cần định nghĩa thêm các DTO dưới đây bên file DTO:
    # SpeakingTopicSummaryResponse,
    # SpeakingSessionStartResponse,
    # SpeakingHistoryItemResponse,
    # SpeakingSessionDetailResponse
)

# Import Service (Tầng xử lý logic nghiệp vụ)
# from .speaking_service import SpeakingService

router = APIRouter()
# speaking_service = SpeakingService()

# ==========================================
# 1. QUẢN LÝ DANH SÁCH ĐỀ THI / TOPICS
# ==========================================

@router.get("/topics")
async def get_speaking_topics(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=50, description="Số lượng đề trên mỗi trang"),
    is_full_test: Optional[bool] = Query(None, description="Lọc theo dạng Full Test hoặc Topic lẻ")
):
    """
    Hiển thị danh sách các bộ đề (Topics) ngoài màn hình chính để user chọn.
    """
    pass
    # return await speaking_service.get_all_topics(page, limit, is_full_test)

@router.get("/topics/{topic_id}/prompts")
async def get_topic_prompts(topic_id: str):
    """
    Xem trước danh sách các câu hỏi (Part 1, 2, 3) có bên trong một bộ đề cụ thể.
    """
    pass
    # return await speaking_service.get_prompts_by_topic(topic_id)


# ==========================================
# 2. KHỞI TẠO BÀI LÀM (SESSIONS)
# ==========================================

@router.post("/topics/{topic_id}/start")
async def start_topic_session(
    topic_id: str,
    test_type: str = Query(..., description="Có thể là FULL_TEST hoặc PART_1, PART_2..."),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Bắt đầu làm một bộ đề. Hệ thống sẽ tạo UserSpeakingTestSessionModel với status = IN_PROGRESS.
    Trả về session_id và câu hỏi đầu tiên.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.start_session_by_topic(user_id, topic_id, test_type)

@router.post("/prompts/{prompt_id}/start")
async def start_prompt_session(
    prompt_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Bắt đầu làm 1 câu hỏi lẻ (Luyện tập ngẫu nhiên/Shadowing).
    Tương tự tạo Session nhưng chỉ link tới prompt_id.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.start_session_by_prompt(user_id, prompt_id)


# ==========================================
# 3. QUÁ TRÌNH LÀM BÀI (THU ÂM & NỘP TỪNG PHẦN)
# ==========================================

@router.post("/sessions/{session_id}/segments")
async def submit_speaking_segment(
    session_id: str,
    prompt_id: str = Form(..., description="ID của câu hỏi đang trả lời"),
    audio_file: UploadFile = File(..., description="File âm thanh user vừa thu âm (.webm, .wav, .m4a)"),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Nộp file audio cho một câu hỏi cụ thể trong session.
    Hệ thống sẽ upload lên cloud, gọi AI Speech-to-Text chuyển thành văn bản, 
    và lưu transcript vào questions_detail của session.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.process_and_save_segment(user_id, session_id, prompt_id, audio_file)


# ==========================================
# 4. HOÀN THÀNH & PHÂN TÍCH AI (SUBMIT & EVALUATE)
# ==========================================

@router.post("/sessions/{session_id}/submit", response_model=SpeakingSubmitResponse)
async def complete_speaking_test(
    session_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    User bấm nộp bài. Hệ thống gom tất cả transcript của session, 
    chạy AI phân tích 4 tiêu chí IELTS, tính điểm và cập nhật session thành COMPLETED.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.evaluate_session(user_id, session_id)

@router.get("/sessions/{session_id}")
async def get_session_result(
    session_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Lấy toàn bộ kết quả phân tích, band score, điểm mạnh, điểm yếu 
    để render màn hình Result Analysis.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.get_session_detail(user_id, session_id)


# ==========================================
# 5. LỊCH SỬ HỌC TẬP (HISTORY)
# ==========================================

@router.get("/history")
async def get_speaking_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Lấy danh sách các bài Speaking user đã hoàn thành (Dùng cho tab Lịch sử học tập).
    """
    user_id = current_user.get("_id") or current_user.get("id")
    pass
    # return await speaking_service.get_user_history(user_id, page, limit)