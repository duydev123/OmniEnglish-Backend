# modules/Listening/listening_controller.py

from fastapi import APIRouter, HTTPException
from .listening_service import ListeningService
from .listening_dto import (
    ListeningSessionStartResponse,
    ListeningDraftRequest,
    ListeningDraftResponse,
    ListeningSubmitResponse
)

router = APIRouter()
listening_service = ListeningService()


@router.get(path="/passages/{passage_id}/start", response_model=ListeningSessionStartResponse)
async def start_listening_session(passage_id: str):
    """Lấy file audio, transcript song ngữ, từ vựng và danh sách câu hỏi"""
    try:
        # 1. Lấy passage
        passage = await listening_service.get_passage(passage_id)
        
        # 2. Tạo hoặc lấy session (tạm thời dùng user_id cố định)
        user_id = "test_user_001"
        session = await listening_service.get_or_create_session(
            user_id, 
            passage_id, 
            session_type="COMPREHENSION"
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
            completions=completions
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
            "updated_at": session.updated_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")