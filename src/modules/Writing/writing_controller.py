from fastapi import HTTPException
from modules.Writing.Writing_dto import AnswerQuestionPayload
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, Query
from modules.User.user_util import UserUtil
from .Writing_dto import (
    WritingPromptResponse,
    WritingDraftRequest,
    WritingDraftResponse,
    WritingSubmitResponse,
    AIAssistanceRequest,
    AIOutlineResponse,
    AICollocationsResponse,
    AISampleEssayResponse,
    ImprovedEssaySampleResponse
)
from .writing_service import WritingService

router = APIRouter()

@router.get(path="/prompts", response_model=List[WritingPromptResponse])
async def get_writing_prompts(
    task_type: Optional[str] = Query(None, description="WITH_GRAPH or WITHOUT_GRAPH"),
    user_dict: Optional[dict] = Depends(UserUtil.ProtectOptional)
):
    """Lấy danh sách đề bài Writing (lọc theo task_type: WITH_GRAPH / WITHOUT_GRAPH)"""
    user_id = None
    if user_dict:
        user_id = str(user_dict.get("id") or user_dict.get("_id") or "")
        if not user_id:
            user_id = None
    return await WritingService.get_writing_prompts(task_type=task_type, user_id=user_id)

@router.get(path="/prompts/{prompt_id}", response_model=WritingPromptResponse)
async def get_writing_prompt(
    prompt_id: str,
    user_dict: Optional[dict] = Depends(UserUtil.ProtectOptional)
):
    """Lấy thông tin đề bài Writing chi tiết kèm cấu trúc dàn bài & từ vựng gợi ý"""
    user_id = None
    if user_dict:
        user_id = str(user_dict.get("id") or user_dict.get("_id") or "")
        if not user_id:
            user_id = None
    return await WritingService.get_writing_prompt(prompt_id=prompt_id, user_id=user_id)

@router.post(path="/prompts/{prompt_id}/ai-assistance")
async def get_ai_assistance(
    prompt_id: str,
    payload: AIAssistanceRequest,
    user_dict: Optional[dict] = Depends(UserUtil.ProtectOptional)
):
    """Hỗ trợ AI trợ lý viết bài (UC-09 Outline, UC-10 Collocations, UC-11 Sample Essay)"""
    return await WritingService.generate_ai_assistance(
        action=payload.action,
        prompt_id=prompt_id,
        user_notes=payload.user_notes,
        difficulty=payload.difficulty or "medium"
    )

@router.post(path="/sessions/draft", response_model=WritingDraftResponse)
async def save_writing_draft(
    payload: WritingDraftRequest,
    user_dict: dict = Depends(UserUtil.Protect)
):
    """Lưu nháp bài essay real-time khi đang soạn thảo"""
    user_id = user_dict.get("id") or user_dict.get("_id") or "user_123"
    return await WritingService.save_writing_draft(user_id=str(user_id), payload=payload)

@router.post(path="/sessions/submit", response_model=WritingSubmitResponse)
async def submit_writing_essay(
    payload: WritingDraftRequest,
    user_dict: dict = Depends(UserUtil.Protect)
):
    """Nộp bài essay và nhận đánh giá AI 4 tiêu chí IELTS (UC-13, UC-14)"""
    user_id = user_dict.get("id") or user_dict.get("_id") or "user_123"
    return await WritingService.submit_writing_essay(user_id=str(user_id), payload=payload)

@router.get(path="/sessions/{session_id}", response_model=WritingSubmitResponse)
async def get_writing_submission(
    session_id: str,
    user_dict: dict = Depends(UserUtil.Protect)
):
    """Xem báo cáo đánh giá bài viết từ lịch sử"""
    user_id = user_dict.get("id") or user_dict.get("_id") or "user_123"
    return await WritingService.get_writing_submission(session_id=session_id, user_id=str(user_id))

@router.post(path="/sessions/{session_id}/improved-sample", response_model=ImprovedEssaySampleResponse)
async def get_improved_essay_sample(
    session_id: str,
    user_dict: dict = Depends(UserUtil.Protect)
):
    """Xem phiên bản essay nâng cấp từ AI dựa trên bài viết của user (UC-15)"""
    user_id = user_dict.get("id") or user_dict.get("_id") or "user_123"
    return await WritingService.generate_improved_essay_sample(session_id=session_id, user_id=str(user_id))

@router.post(path="/prompts/{prompt_id}/answer")
async def answer_question(
    prompt_id: str,
    payload: AnswerQuestionPayload,
    user_dict: Optional[dict] = Depends(UserUtil.ProtectOptional)
):
    """Trả lời câu hỏi tự do của user về đề bài"""
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    return await WritingService.answer_custom_question(prompt_id, payload.question.strip())