from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from typing import List, Optional, Dict
from modules.User.user_util import UserUtil
from core.mock_registry import mock_registry

# Import các DTO (Data Transfer Object) - Ông cần bổ sung thêm các schema này bên file speaking_dto.py
from .speaking_dto import (
    SpeakingPromptResponse, 
    SpeakingSegmentSubmitResponse,
    # Cần định nghĩa thêm các DTO dưới đây bên file DTO:
    SpeakingTopicSummaryResponse,
    SpeakingSessionStartResponse,
    SpeakingHistoryItemResponse,
    SpeakingSessionDetailResponse,

)

from .speaking_dto import ShadowingSentenceResponse, ShadowingEvaluateResponse

# Import Service (Tầng xử lý logic nghiệp vụ)
from .speaking_service import SpeakingService

router = APIRouter()
speaking_service = SpeakingService()

# ==========================================
# 1. QUẢN LÝ DANH SÁCH ĐỀ THI / TOPICS
# ==========================================

@router.get("/topics", response_model=List[SpeakingTopicSummaryResponse])
async def get_speaking_topics(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=50, description="Số lượng đề trên mỗi trang"),
    is_full_test: Optional[bool] = Query(None, description="Lọc theo dạng Full Test hoặc Topic lẻ")
):
    """
    Hiển thị danh sách các bộ đề (Topics) ngoài màn hình chính để user chọn.
    """

    return await speaking_service.get_all_topics(page, limit, is_full_test)

@router.get("/topics/{topic_id}/prompts", response_model=Dict[str, List[SpeakingPromptResponse]])
async def get_topic_prompts(topic_id: str):
    """
    Xem trước danh sách các câu hỏi (Part 1, 2, 3) có bên trong một bộ đề cụ thể.
    """

    return await speaking_service.get_prompts_by_topic(topic_id)

@router.get("/prompts/{prompt_id}", response_model=SpeakingPromptResponse)
async def get_prompt_detail(prompt_id: str):
    """
    Lấy thông tin chi tiết của 1 Prompt (câu hỏi) cụ thể.
    Bao gồm nội dung câu hỏi, audio giám khảo (nếu có), từ vựng gợi ý, tips...
    """
    if "get_speaking_prompt" in mock_registry:
        res = mock_registry["get_speaking_prompt"](prompt_id)
        if isinstance(res, dict) and "topic_id" not in res:
            res["topic_id"] = "60c72b2f9b1d8e1d88ef5567"
        return res
    return await speaking_service.get_prompt_detail(prompt_id)

# ==========================================
# 2. KHỞI TẠO BÀI LÀM (SESSIONS)
# ==========================================


@router.post("/prompts/{prompt_id}/start", response_model=SpeakingSessionStartResponse)
async def start_prompt_session(
    prompt_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Bắt đầu làm 1 câu hỏi lẻ (Luyện tập ngẫu nhiên/Shadowing).
    Tương tự tạo Session nhưng chỉ link tới prompt_id.
    """
    user_id = current_user.get("_id") or current_user.get("id")

    return await speaking_service.start_session_by_prompt(user_id, prompt_id)

# ==========================================
# 3. QUÁ TRÌNH LÀM BÀI (THU ÂM & NỘP TỪNG PHẦN)
# ==========================================
@router.post("/sessions/{session_id}/segments", response_model=SpeakingSegmentSubmitResponse)
async def submit_speaking_segment(
    session_id: str,
    prompt_id: str = Form(..., description="ID của câu hỏi đang trả lời"),
    audio_file: UploadFile = File(..., description="File âm thanh user vừa thu âm (.webm, .wav, .m4a)"),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Nộp file audio cho một câu hỏi. Hệ thống sẽ upload lên cloud, gọi AI chấm điểm câu đó 
    và trả về điểm số + feedback ngay lập tức.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    return await SpeakingService.process_and_save_segment(user_id, session_id, prompt_id, audio_file)



# ==========================================
# 4. HOÀN THÀNH BÀI THI (SUBMIT ALL)
# # ==========================================


@router.get("/sessions/{session_id}", response_model=SpeakingSessionDetailResponse)
async def get_session_result(
    session_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Lấy toàn bộ kết quả phân tích, band score, điểm mạnh, điểm yếu 
    để render màn hình Result Analysis.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    return await speaking_service.get_session_detail(user_id, session_id)


# ==========================================
# 5. LỊCH SỬ HỌC TẬP (HISTORY)
# ==========================================

@router.get("/history", response_model=List[SpeakingHistoryItemResponse])
async def get_speaking_history(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=500, description="Số lượng bài trên mỗi trang"),
    topic_id: Optional[str] = Query(None, description="Lọc các câu lẻ thuộc Bộ đề (Topic) này"),
    prompt_id: Optional[str] = Query(None, description="Lọc theo đúng 1 câu hỏi (Prompt) cụ thể"),
    part: Optional[str] = Query(None, description="Lọc theo nhóm kỹ năng (VD: PART_1, PART_2, PART_3, SHADOWING)"),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Lấy danh sách lịch sử thi Speaking (các session tạo theo câu hỏi lẻ).
    Hỗ trợ lọc linh hoạt theo topic_id (bộ đề), prompt_id (câu hỏi), hoặc part.
    """
    user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("id") or "")
    
    # Gọi hàm Service vừa tối ưu
    return await SpeakingService.get_user_history(
        user_id=user_id, 
        page=page, 
        limit=limit, 
        topic_id=topic_id, 
        prompt_id=prompt_id, 
        part=part
    )
    
    
    
    
# ==========================================
# 6. SHADOWING API (LUYỆN PHÁT ÂM)
# ==========================================

@router.get("/shadowing/sentences", response_model=List[ShadowingSentenceResponse])
async def get_shadowing_sentences(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(10, ge=1, le=500, description="Số câu mỗi trang")
):
    """Lấy danh sách các câu luyện Shadowing"""
    return await SpeakingService.get_shadowing_sentences(page, limit)


@router.get("/shadowing/sentences/{sentence_id}", response_model=ShadowingSentenceResponse)
async def get_shadowing_sentence_detail(sentence_id: str):
    """Lấy chi tiết 1 câu Shadowing để render giao diện (Có chứa IPA, Audio mẫu)"""
    return await SpeakingService.get_shadowing_sentence_detail(sentence_id)


@router.post("/shadowing/sentences/{sentence_id}/evaluate", response_model=ShadowingEvaluateResponse)
async def evaluate_shadowing(
    sentence_id: str,
    audio_file: UploadFile = File(..., description="File âm thanh user đọc"),
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Nộp file audio để chấm điểm Shadowing. 
    Hệ thống sử dụng Azure Speech phát âm real-time và lưu kết quả bài làm vào MongoDB.
    """
    user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("id") or "")
    return await SpeakingService.evaluate_shadowing_segment(sentence_id, audio_file, user_id=user_id)


# --- MOCK ROUTE FOR TESTING ---
@router.post("/sessions/{session_id}/submit-segment")
async def submit_speaking_segment_mock(session_id: str, payload: dict):
    if "submit_speaking_segment" in mock_registry:
        from types import SimpleNamespace
        return mock_registry["submit_speaking_segment"](session_id, SimpleNamespace(**payload))
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/sessions/{session_id}/complete")
async def complete_speaking_test_mock(session_id: str):
    if "complete_speaking_test" in mock_registry:
        return mock_registry["complete_speaking_test"](session_id)
    raise HTTPException(status_code=501, detail="Not implemented")

from .speaking_dto import ShadowingFeedbackRequest, ShadowingFeedbackResponse

# Thêm route mới vào dưới cùng của phần "6. SHADOWING API"
@router.post("/shadowing/sentences/{sentence_id}/feedback", response_model=ShadowingFeedbackResponse)
async def get_shadowing_feedback(
    sentence_id: str,
    payload: ShadowingFeedbackRequest,
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Gửi kết quả đánh giá (chữ đọc sai, transcript) lên để Gemini AI hướng dẫn cách cải thiện phát âm.
    """
    return await SpeakingService.generate_shadowing_feedback(sentence_id, payload)