from fastapi import APIRouter
from classes.WritingClass import (
    WritingPromptResponse,
    WritingDraftRequest,
    WritingDraftResponse,
    WritingSubmitResponse
)

router = APIRouter()

@router.get(path="/prompts/{prompt_id}", response_model=WritingPromptResponse)
async def get_writing_prompt(prompt_id: str):
    """Lấy đề bài Writing kèm gợi ý dàn bài & từ vựng nâng cao"""
    pass

@router.patch(path="/sessions/{session_id}/draft", response_model=WritingDraftResponse)
async def save_writing_draft(session_id: str, payload: WritingDraftRequest):
    """Lưu nháp bài essay đang gõ real-time"""
    pass

@router.post(path="/sessions/{session_id}/submit", response_model=WritingSubmitResponse)
async def submit_writing_essay(session_id: str, payload: WritingDraftRequest):
    """Nộp bài essay và nhận kết quả chấm AI (4 tiêu chí IELTS, highlight lỗi)"""
    pass