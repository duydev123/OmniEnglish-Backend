from fastapi import APIRouter
from classes.ReadingClass import (
    ReadingSessionStartResponse
)

router = APIRouter()

@router.get(path="/passages/{passage_id}/start", response_model=ReadingSessionStartResponse)
async def start_reading_session(passage_id: str):
    """Lấy bài đọc bên trái và 3 dạng câu hỏi bên phải"""
    pass

@router.patch(path="/sessions/{session_id}/draft")
async def save_reading_draft(session_id: str, payload: dict):
    """Lưu nháp bài đọc khi user đang làm dở"""
    pass

@router.post(path="/sessions/{session_id}/submit")
async def submit_reading_answers(session_id: str, payload: dict):
    """Chấm điểm bài đọc và trả về kết quả"""
    pass