# modules/Listening/listening_controller.py

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from .listening_service import ListeningService
from .listening_dto import (
    ListeningSessionStartResponse,
    ListeningDraftRequest,
    ListeningDraftResponse,
    ListeningSubmitResponse,
    ListeningPassageListResponse,
    ListeningPassageDetailResponse
)
from modules.User.user_util import UserUtil

router = APIRouter()
listening_service = ListeningService()


@router.get(path="/passages", response_model=ListeningPassageListResponse)
async def list_listening_passages(
    page: int = 1,
    limit: int = 10,
    question_type: Optional[str] = None
):
    """Liệt kê các passage listening có sẵn để frontend chọn bài."""
    try:
        items, total = await listening_service.list_passages(page=page, limit=limit, question_type=question_type)
        return ListeningPassageListResponse(items=items, page=page, limit=limit, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/passages/{passage_id}", response_model=ListeningPassageDetailResponse)
async def get_listening_passage_detail(passage_id: str):
    """Lấy thông tin chi tiết của một passage listening."""
    try:
        passage = await listening_service.get_passage(passage_id)
        return ListeningPassageDetailResponse(
            id=str(passage.id),
            title=passage.title,
            unit_code=passage.unit_code,
            audio_url=passage.audio_url,
            interactive_transcript=await listening_service.format_transcript(passage),
            key_vocabulary=await listening_service.format_vocabulary(passage),
            time_limit_minutes=passage.time_limit_minutes,
            total_questions=passage.total_questions,
            created_at=passage.created_at.isoformat() if getattr(passage, 'created_at', None) else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/passages/{passage_id}/start", response_model=ListeningSessionStartResponse)
async def start_listening_session(passage_id: str, session_type: str = "COMPREHENSION", current_user: dict = Depends(UserUtil.Protect)):
    """Lấy file audio, transcript song ngữ, từ vựng và danh sách câu hỏi"""
    try:
        # 1. Lấy passage
        passage = await listening_service.get_passage(passage_id)
        
        # 2. Tạo hoặc lấy session
        user_id = str(current_user.get("id") or current_user.get("_id") or "")
        session = await listening_service.get_or_create_session(
            user_id, 
            passage_id, 
            session_type=session_type
        )
        
        # 3. Format dữ liệu
        transcript = await listening_service.format_transcript(passage)
        vocabulary = await listening_service.format_vocabulary(passage)
        multiple_choices = await listening_service.format_multiple_choices(passage_id)
        completions = await listening_service.format_completions(passage_id)
        
        # 4. Trả về response
        return ListeningSessionStartResponse(
            session_id=str(session.id),
            passage_id=passage_id,
            title=passage.title,
            unit_code=passage.unit_code,
            audio_url=passage.audio_url,
            time_limit_minutes=passage.time_limit_minutes,
            interactive_transcript=transcript,
            key_vocabulary=vocabulary,
            completed_questions=session.completed_questions,
            total_questions=passage.total_questions,
            multiple_choices=multiple_choices,
            completions=completions,
            user_answers=session.user_answers or {},
            user_typed_text=session.user_typed_text,
            time_remaining_seconds=session.time_remaining_seconds if session.time_remaining_seconds is not None else (passage.time_limit_minutes * 60)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch(path="/sessions/{session_id}/draft", response_model=ListeningDraftResponse)
async def save_listening_draft(session_id: str, payload: ListeningDraftRequest):
    """Lưu nháp bài nghe (Comprehension) hoặc lưu chữ chép chính tả (Dictation)"""
    try:
        if payload.session_type == "COMPREHENSION":
            result = await listening_service.save_comprehension_draft(
                session_id=session_id,
                user_answers=payload.user_answers,
                time_remaining_seconds=payload.time_remaining_seconds
            )
        else:  # DICTATION
            result = await listening_service.save_dictation_draft(
                session_id=session_id,
                user_typed_text=payload.user_typed_text or ""
            )
        
        return ListeningDraftResponse(
            session_id=session_id,
            status="IN_PROGRESS",
            message=result["message"]
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(path="/sessions/{session_id}/submit", response_model=ListeningSubmitResponse)
async def submit_listening_answers(session_id: str, payload: ListeningDraftRequest):
    """Nộp bài nghe, nhận báo cáo phân tích ma trận kỹ năng hoặc tô màu chép chính tả"""
    try:
        if payload.session_type == "COMPREHENSION":
            result = await listening_service.grade_comprehension(
                session_id=session_id,
                user_answers=payload.user_answers
            )
        else:  # DICTATION
            result = await listening_service.grade_dictation(
                session_id=session_id,
                user_typed_text=payload.user_typed_text or ""
            )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
@router.get(path="/sessions/{session_id}/draft")
async def get_listening_draft(session_id: str):
    """Lấy nháp bài nghe đã lưu"""
    try:
        result = await listening_service.get_draft(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(path="/users/{user_id}/history")
async def get_user_listening_history(
    user_id: str,
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None
):
    """Lấy danh sách lịch sử/nháp làm bài nghe của user"""
    try:
        return await listening_service.get_user_history(user_id=user_id, page=page, limit=limit, status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(path="/sessions/{session_id}")
async def get_listening_session(session_id: str):
    """Lấy thông tin session listening"""
    try:
        session = await listening_service.get_session(session_id)
        passage = await session.passage_id.fetch()
        
        return {
            "success": True,
            "session_id": str(session.id),
            "user_id": session.user_id,
            "passage_id": str(passage.id),
            "passage_title": passage.title,
            "session_type": session.session_type,
            "status": session.status,
            "accuracy_rate": session.accuracy_rate,
            "score_summary": session.score_summary,
            "xp_earned": session.xp_earned,
            "competency_matrix": session.competency_matrix,
            "detailed_question_review": session.detailed_question_review,
            "words_typed": session.words_typed,
            "wpm": session.wpm,
            "missed_contractions": session.missed_contractions,
            "transcript_comparison": session.transcript_comparison,
            "spelling_tip": session.spelling_tip,
            "listening_insight": session.listening_insight,
            "start_at": session.start_at,
            "updated_at": session.updated_at,
            "audio_url": passage.audio_url,
            "interactive_transcript": await listening_service.format_transcript(passage)
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(path="/questions/{question_id}/audio-segment")
async def get_question_audio_segment(question_id: str):
    """Lấy audio segment và transcript segment theo question_id"""
    try:
        result = await listening_service.get_audio_segment_by_question(question_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")