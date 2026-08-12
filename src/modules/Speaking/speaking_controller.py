from fastapi import APIRouter
from .speaking_dto import SpeakingPromptResponse, SpeakingSegmentSubmitRequest, SpeakingSubmitResponse
from core.mock_registry import mock_registry

router = APIRouter()

@router.get("/prompts/{prompt_id}", response_model=SpeakingPromptResponse)
async def get_speaking_prompt(prompt_id: str):
    """Lấy đề bài Speaking kèm từ vựng gợi ý"""
    if "get_speaking_prompt" in mock_registry:
        return mock_registry["get_speaking_prompt"](prompt_id)
    pass

@router.post("/sessions/{session_id}/submit-segment")
async def submit_speaking_segment(session_id: str, payload: SpeakingSegmentSubmitRequest):
    """Bắn file ghi âm & chữ nhận diện (Real-time) lên Server từng câu một"""
    if "submit_speaking_segment" in mock_registry:
        return mock_registry["submit_speaking_segment"](session_id, payload)
    pass

@router.post("/sessions/{session_id}/complete", response_model=SpeakingSubmitResponse)
async def complete_speaking_test(session_id: str):
    """Báo hoàn thành lượt thi, AI trả về báo cáo 4 tiêu chí IELTS chuyên sâu"""
    if "complete_speaking_test" in mock_registry:
        return mock_registry["complete_speaking_test"](session_id)
    pass