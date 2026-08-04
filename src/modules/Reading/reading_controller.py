from fastapi import APIRouter, HTTPException
from typing import Dict
from .reading_service import ReadingService
from .Reading_dto import (
    ReadingSessionStartResponse,
    ReadingDraftRequest,
    ReadingSubmitRequest,
    ReadingSubmitResponse
)

router = APIRouter()
reading_service = ReadingService()


@router.get(path="/passages/{passage_id}/start", response_model=ReadingSessionStartResponse)
async def start_reading_session(passage_id: str):
    """Bắt đầu session làm bài Reading"""
    try:
        # 1. Lấy passage
        passage = await reading_service.get_passage(passage_id)
        
        # 2. Tạo hoặc lấy session (tạm thời dùng user_id cố định)
        user_id = "test_user_001"
        session = await reading_service.get_or_create_session(user_id, passage_id)
        
        # 3. Format các loại câu hỏi
        multiple_choices = await reading_service.format_multiple_choices(passage_id)
        heading_matchings = await reading_service.format_heading_matchings(passage, passage_id)
        fill_blanks = await reading_service.format_fill_blanks(passage_id)
        true_false_not_given = await reading_service.format_true_false_not_given(passage_id)
        
        # 4. Trả về response
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
            true_false_not_given=true_false_not_given
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")