from fastapi import APIRouter
from .listening_dto import (
    ListeningSessionStartResponse,
    ListeningDraftRequest,
    ListeningDraftResponse,
    ListeningSubmitResponse
)

router = APIRouter()

@router.get(path="/passages/{passage_id}/start", response_model=ListeningSessionStartResponse)
async def start_listening_session(passage_id: str):
    """Lấy file audio, transcript song ngữ, từ vựng và danh sách câu hỏi"""
    pass

@router.patch(path="/sessions/{session_id}/draft", response_model=ListeningDraftResponse)
async def save_listening_draft(session_id: str, payload: ListeningDraftRequest):
    """Lưu nháp bài nghe (Comprehension) hoặc lưu chữ chép chính tả (Dictation)"""
    pass

@router.post(path="/sessions/{session_id}/submit", response_model=ListeningSubmitResponse)
async def submit_listening_answers(session_id: str, payload: ListeningDraftRequest):
    """Nộp bài nghe, nhận báo cáo phân tích ma trận kỹ năng hoặc tô màu chép chính tả"""
    pass