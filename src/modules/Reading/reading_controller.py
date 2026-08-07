import logging
import traceback
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional
from .reading_service import ReadingService

logger = logging.getLogger("omni_english")

from .Reading_dto import (
    ReadingSessionStartResponse,
    ReadingDraftRequest,
    ReadingSubmitRequest,
    ReadingSubmitResponse,
    ReadingSessionDetailResponse,
    PassageListResponse,
    PassageDetailResponse,
    UserHistoryListResponse,
    UserReadingStatsResponse,
    ReadingSessionReviewResponse,
    ReadingVocabularyBookmarkRequest,
    ReadingVocabularyBookmarkResponse
)

router = APIRouter()
reading_service = ReadingService()


@router.get(path="/passages/{passage_id}/start", response_model=ReadingSessionStartResponse)
async def start_reading_session(passage_id: str):
    """Bắt đầu session làm bài Reading"""
    try:
        passage = await reading_service.get_passage(passage_id)
        user_id = "test_user_001"
        session = await reading_service.get_or_create_session(user_id, passage_id)
        
        multiple_choices = await reading_service.format_multiple_choices(passage_id)
        heading_matchings = await reading_service.format_heading_matchings(passage, passage_id)
        fill_blanks = await reading_service.format_fill_blanks(passage_id)
        true_false_not_given = await reading_service.format_true_false_not_given(passage_id)
        
        return ReadingSessionStartResponse(
            session_id=str(session.id),
            title=passage.title,
            content=passage.content,
            image_url=passage.image_url,
            learning_tip=passage.learning_tip,
            completed_questions=session.completed_questions,
            total_questions=passage.total_questions,
            time_remaining_seconds=session.time_remaining_seconds,
            multiple_choices=multiple_choices,
            heading_matchings=heading_matchings,
            fill_blanks=fill_blanks,
            true_false_not_given=true_false_not_given,
            user_answers=session.user_answers
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[start_reading_session] passage_id={passage_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch(path="/sessions/{session_id}/draft")
async def save_reading_draft(session_id: str, payload: ReadingDraftRequest):
    """Lưu nháp bài đọc khi user đang làm dở"""
    try:
        result = await reading_service.save_draft(
            session_id=session_id,
            time_remaining_seconds=payload.time_remaining_seconds,
            user_answers=payload.user_answers
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[save_reading_draft] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/sessions/{session_id}/draft")
async def get_reading_draft(session_id: str):
    """Lấy nháp bài đọc đã lưu"""
    try:
        result = await reading_service.get_draft(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[get_reading_draft] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(path="/sessions/{session_id}/submit", response_model=ReadingSubmitResponse)
async def submit_reading_answers(session_id: str, payload: ReadingSubmitRequest):
    """Chấm điểm bài đọc và trả về kết quả"""
    try:
        result = await reading_service.submit_answers(
            session_id=session_id,
            user_answers=payload.user_answers,
            time_remaining=payload.time_remaining_seconds
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[submit_reading_answers] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/sessions/{session_id}", response_model=ReadingSessionDetailResponse)
async def get_session_details(session_id: str):
    """Lấy toàn bộ thông tin session (tiến độ, điểm số, v.v.)"""
    try:
        return await reading_service.get_session_details(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[get_session_details] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/passages", response_model=PassageListResponse)
async def get_passages(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    level: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None),
    question_type: Optional[str] = Query(default=None)
):
    """Lấy danh sách các bài đọc có sẵn"""
    try:
        return await reading_service.get_passages(page=page, limit=limit, level=level, topic=topic, question_type=question_type)
    except Exception as e:
        logger.error(f"[get_passages]\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/passages/{passage_id}", response_model=PassageDetailResponse)
async def get_passage_detail(passage_id: str):
    """Lấy thông tin chi tiết của một passage"""
    try:
        return await reading_service.get_passage_detail(passage_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[get_passage_detail] passage_id={passage_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/users/{user_id}/history", response_model=UserHistoryListResponse)
async def get_user_history(
    user_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None)
):
    """Lấy danh sách các bài đọc user đã làm"""
    try:
        return await reading_service.get_user_history(user_id=user_id, page=page, limit=limit, status=status)
    except Exception as e:
        logger.error(f"[get_user_history] user_id={user_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete(path="/sessions/{session_id}")
async def delete_session(session_id: str):
    """Hủy session đang làm dở (nếu user muốn bắt đầu lại)"""
    try:
        return await reading_service.delete_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[delete_session] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/users/{user_id}/stats", response_model=UserReadingStatsResponse)
async def get_user_stats(user_id: str):
    """Lấy thống kê tổng quan về performance của user trong Reading"""
    try:
        return await reading_service.get_user_stats(user_id)
    except Exception as e:
        logger.error(f"[get_user_stats] user_id={user_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/sessions/{session_id}/review", response_model=ReadingSessionReviewResponse)
async def get_session_review(session_id: str):
    """Lấy chi tiết bài review (đã có trong /submit nhưng dùng riêng)"""
    try:
        return await reading_service.get_session_review(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[get_session_review] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(path="/sessions/{session_id}/vocabulary", response_model=ReadingVocabularyBookmarkResponse)
async def bookmark_vocabulary(session_id: str, payload: ReadingVocabularyBookmarkRequest):
    """Lưu từ vựng user muốn ghi nhớ trong bài đọc"""
    try:
        return await reading_service.bookmark_vocabulary(
            session_id=session_id,
            word=payload.word,
            context=payload.context
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[bookmark_vocabulary] session_id={session_id}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
