from fastapi import APIRouter
from .Grammar_dto import (
    GrammarSessionStartResponse,
    GrammarGuideResponse,
    GrammarDraftRequest,
    GrammarDraftResponse,
    GrammarSubmitResponse
)
from core.mock_registry import mock_registry

router = APIRouter()

@router.get(path="/topics/{topic_id}/start", response_model=GrammarSessionStartResponse)
async def start_grammar_session(topic_id: str):
    """Lấy danh sách bài tập ngữ pháp (4 dạng) kèm Grammar Guide ở cột bên phải"""
    if "start_grammar_session" in mock_registry:
        return mock_registry["start_grammar_session"](topic_id)
    return GrammarSessionStartResponse(
        session_id=f"session_{topic_id}",
        topic_id=topic_id,
        title="Grammar Practice",
        level="Intermediate B2",
        guide=GrammarGuideResponse(
            rule_title="General Grammar Rules",
            rule_description="Practice sentence structure and grammar usage.",
            formula="Subject + Verb + Object",
            quick_reference=[]
        ),
        completed_tasks=0,
        total_tasks=5,
        questions=[]
    )

@router.patch(path="/sessions/{session_id}/draft", response_model=GrammarDraftResponse)
async def save_grammar_draft(session_id: str, payload: GrammarDraftRequest):
    """Lưu nháp đáp án các câu ngữ pháp user đang chọn/điền"""
    if "save_grammar_draft" in mock_registry:
        return mock_registry["save_grammar_draft"](session_id, payload)
    return GrammarDraftResponse(session_id=session_id, status="IN_PROGRESS", message="Draft saved successfully")

@router.post(path="/sessions/{session_id}/submit", response_model=GrammarSubmitResponse)
async def submit_grammar_answers(session_id: str, payload: GrammarDraftRequest):
    """Chấm điểm bài ngữ pháp, tính Accuracy Rate và cộng điểm XP"""
    if "submit_grammar_answers" in mock_registry:
        return mock_registry["submit_grammar_answers"](session_id, payload)
    return GrammarSubmitResponse(
        session_id=session_id,
        status="COMPLETED",
        score=len(payload.user_answers),
        total_tasks=max(1, len(payload.user_answers)),
        accuracy_rate=100.0 if payload.user_answers else 0.0,
        xp_earned=10,
        practice_time_seconds=payload.practice_time_seconds,
        detailed_results={}
    )