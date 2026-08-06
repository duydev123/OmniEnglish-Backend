# modules/Listening/listening_controller.py
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

from .listening_service import ListeningService
from .listening_dto import (
    # Passages & History
    ListeningPassageSummaryResponse,
    ListeningHistoryItemResponse,
    
    # Comprehension
    ComprehensionSessionStartResponse,
    ListeningDraftRequest,
    ListeningDraftResponse,
    ListeningSubmitResponse,
    
    # Dictation
    DictationSessionStartResponse,
    DictationSentenceGradeRequest,
    DictationSentenceGradeResponse
)

router = APIRouter()

# ==========================================
# 1. NHÓM QUẢN LÝ BÀI HỌC (PASSAGES) & LỊCH SỬ
# ==========================================

@router.get(path="/passages", response_model=List[ListeningPassageSummaryResponse])
async def get_available_passages(
    page: int = Query(1, ge=1, description="Số trang hiện tại"),
    limit: int = Query(10, ge=1, le=50, description="Số lượng bài mỗi trang")
):
    """Lấy danh sách các bài Listening có sẵn (Có phân trang)"""
    try:
        return await ListeningService.get_all_passages(page, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/passages/{passage_id}")
async def get_passage_detail(passage_id: str):
    """Xem chi tiết 1 bài trước khi làm (Mô tả, độ khó, điểm cao nhất của user...)"""
    try:
        user_id = "test_user_001" # TODO: Thay bằng current_user từ JWT Token
        return await ListeningService.get_passage_detail(passage_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/history", response_model=List[ListeningHistoryItemResponse])
async def get_listening_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    """Xem lại lịch sử các bài Listening đã hoàn thành (Comprehension & Dictation)"""
    try:
        user_id = "test_user_001" # TODO: Thay bằng current_user từ JWT Token
        return await ListeningService.get_user_history(user_id, page, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 2. NHÓM BÀI LÀM: COMPREHENSION (NGHE HIỂU)
# ==========================================

@router.get(path="/passages/{passage_id}/start-comprehension", response_model=ComprehensionSessionStartResponse)
async def start_comprehension_session(passage_id: str):
    """Khởi tạo bài thi nghe hiểu (Lấy audio, transcript, Multiple choice, Completion)"""
    try:
        user_id = "test_user_001"
        return await ListeningService.start_comprehension_session(user_id, passage_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/sessions/{session_id}/draft")
async def get_comprehension_draft(session_id: str):
    """Lấy lại bản nháp Comprehension đang làm dở (Resume)"""
    try:
        return await ListeningService.get_comprehension_draft(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(path="/sessions/{session_id}/draft", response_model=ListeningDraftResponse)
async def save_comprehension_draft(session_id: str, payload: ListeningDraftRequest):
    """Lưu nháp tiến độ chọn đáp án khi user đang làm bài"""
    try:
        return await ListeningService.save_comprehension_draft(session_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/sessions/{session_id}/submit", response_model=ListeningSubmitResponse)
async def submit_comprehension_answers(session_id: str, payload: ListeningDraftRequest):
    """Nộp bài Comprehension để hệ thống chấm điểm và sinh ma trận phân tích"""
    try:
        return await ListeningService.submit_comprehension_answers(session_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/sessions/{session_id}")
async def get_comprehension_session_result(session_id: str):
    """Xem lại chi tiết bài Comprehension đã nộp (Báo cáo kết quả)"""
    try:
        return await ListeningService.get_comprehension_session_result(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. NHÓM BÀI LÀM: DICTATION (CHÉP CHÍNH TẢ)
# ==========================================

@router.get(path="/passages/{passage_id}/start-dictation", response_model=DictationSessionStartResponse)
async def start_dictation_session(passage_id: str):
    """Khởi tạo bài chép chính tả (Lấy audio, transcript gốc, từ vựng)"""
    try:
        user_id = "test_user_001"
        return await ListeningService.start_dictation_session(user_id, passage_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/dictation-sessions/{session_id}/draft")
async def get_dictation_draft(session_id: str):
    """Lấy lại tiến độ gõ Dictation đang làm dở (Để load lại các câu đã check)"""
    try:
        return await ListeningService.get_dictation_draft(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/dictation-sessions/{session_id}/grade-sentence", response_model=DictationSentenceGradeResponse)
async def check_and_save_dictation_sentence(session_id: str, payload: DictationSentenceGradeRequest):
    """Chấm điểm tức thời và lưu lịch sử gõ của 1 câu riêng lẻ"""
    try:
        return await ListeningService.grade_and_save_dictation_sentence(
            session_id=session_id, 
            transcript_index=payload.transcript_index, 
            user_typed_text=payload.user_typed_text
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/dictation-sessions/{session_id}/submit")
async def submit_dictation_session(session_id: str):
    """Bấm hoàn thành bài Dictation, chốt điểm tổng và khóa Session"""
    try:
        return await ListeningService.submit_dictation_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(path="/dictation-sessions/{session_id}")
async def get_dictation_session_result(session_id: str):
    """Xem lại báo cáo kết quả chi tiết của bài Dictation sau khi đã nộp"""
    try:
        return await ListeningService.get_dictation_session_result(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))