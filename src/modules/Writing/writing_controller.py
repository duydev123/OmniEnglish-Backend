from fastapi import APIRouter
from .Writing_dto import (
    WritingPromptResponse,
    WritingDraftRequest,
    WritingDraftResponse,
    WritingSubmitResponse
)
from core.mock_registry import mock_registry

router = APIRouter()

@router.get(path="/prompts/{prompt_id}", response_model=WritingPromptResponse)
async def get_writing_prompt(prompt_id: str):
    """Lấy đề bài Writing kèm gợi ý dàn bài & từ vựng nâng cao"""
    if "get_writing_prompt" in mock_registry:
        return mock_registry["get_writing_prompt"](prompt_id)
    pass

@router.patch(path="/sessions/{session_id}/draft", response_model=WritingDraftResponse)
async def save_writing_draft(session_id: str, payload: WritingDraftRequest):
    """Lưu nháp bài essay đang gõ real-time"""
    if "save_writing_draft" in mock_registry:
        return mock_registry["save_writing_draft"](session_id, payload)
    pass

@router.post(path="/sessions/{session_id}/submit", response_model=WritingSubmitResponse)
async def submit_writing_essay(session_id: str, payload: WritingDraftRequest):
    """Nộp bài essay và nhận kết quả chấm AI (4 tiêu chí IELTS, highlight lỗi)"""
    if "submit_writing_essay" in mock_registry:
        return mock_registry["submit_writing_essay"](session_id, payload)
    pass