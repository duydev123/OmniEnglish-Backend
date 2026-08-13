from fastapi import APIRouter
from .Grammar_dto import (
    GrammarSessionStartResponse,
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
    pass

@router.patch(path="/sessions/{session_id}/draft", response_model=GrammarDraftResponse)
async def save_grammar_draft(session_id: str, payload: GrammarDraftRequest):
    """Lưu nháp đáp án các câu ngữ pháp user đang chọn/điền"""
    if "save_grammar_draft" in mock_registry:
        return mock_registry["save_grammar_draft"](session_id, payload)
    pass

@router.post(path="/sessions/{session_id}/submit", response_model=GrammarSubmitResponse)
async def submit_grammar_answers(session_id: str, payload: GrammarDraftRequest):
    """Chấm điểm bài ngữ pháp, tính Accuracy Rate và cộng điểm XP"""
    if "submit_grammar_answers" in mock_registry:
        return mock_registry["submit_grammar_answers"](session_id, payload)
    pass