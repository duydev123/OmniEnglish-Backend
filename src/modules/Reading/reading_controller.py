import random
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List
from beanie import PydanticObjectId

from modules.User.user_util import UserUtil
from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel, 
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)
from .Reading_dto import (
    ReadingSessionStartResponse,
    MultipleChoiceResponse,
    HeadingMatchingResponse,
    FillBlankResponse,
    TrueFalseNotGivenResponse,
    ReadingDraftRequest,
    ReadingSubmitRequest,
    ReadingSubmitResponse,
    QuestionResult
)

router = APIRouter()

@router.get(path="/passages")
async def get_all_reading_passages(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    """Lấy danh sách các bài Reading có sẵn (có phân trang) cho Practice Module"""
    skip = (page - 1) * limit
    passages = await ReadingPassageModel.find_all().skip(skip).limit(limit).to_list()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "image_url": getattr(p, "image_url", ""),
            "total_questions": p.total_questions,
            "time_limit_minutes": p.time_limit_minutes,
            "difficulty": getattr(p, "difficulty", "Intermediate")
        }
        for p in passages
    ]

@router.get(path="/passages/{passage_id}/start", response_model=ReadingSessionStartResponse)
async def start_reading_session(
    passage_id: str,
    current_user: dict = Depends(UserUtil.Protect)
):
    # 1. Lấy passage
    passage = await ReadingPassageModel.get(passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="Passage not found")
    
    # Lấy user_id thực tế từ JWT Token
    user_id = current_user.get("_id") or current_user.get("id")
    existing_session = await UserReadingSessionModel.find_one(
        UserReadingSessionModel.user_id == user_id,
        UserReadingSessionModel.passage_id.id == PydanticObjectId(passage_id),
        UserReadingSessionModel.status == "IN_PROGRESS"
    )
    
    if existing_session:
        # Nếu có session đang làm dở, trả về session đó
        session = existing_session
    else:
        # Tạo session mới
        session = UserReadingSessionModel(
            user_id=user_id,
            passage_id=passage,
            total_questions=passage.total_questions,
            time_remaining_seconds=passage.time_limit_minutes * 60,
            attempt_number=1,
            status="IN_PROGRESS"
        )
        await session.insert()
    # 3. Lấy các câu hỏi
    multiple_choices = await ReadingMultipleChoiceModel.find(
        ReadingMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
    ).to_list()

    heading_matchings = await ReadingHeadingMatchingModel.find(
        ReadingHeadingMatchingModel.passage_id.id == PydanticObjectId(passage_id)
    ).to_list()
    
    fill_blanks = await ReadingFillBlankModel.find(
        ReadingFillBlankModel.passage_id.id == PydanticObjectId(passage_id)
    ).to_list()
    true_false_not_given = await ReadingTrueFalseNotGivenModel.find(
        ReadingTrueFalseNotGivenModel.passage_id.id == passage.id
    ).to_list()
    
    # Format heading matchings - Lấy headings và paragraphs
    heading_responses = []
    for h in heading_matchings:
        # Lấy nội dung các paragraph từ passage (cần có logic tách paragraph)
        # Giả sử passage.content được chia thành các paragraph bằng \n\n
        paragraphs = [p.strip() for p in passage.content.split('\n\n') if p.strip()]
        # Chỉ lấy số paragraph tương ứng với số heading cần match
        # (thực tế nên lấy từ cấu trúc dữ liệu, ở đây demo)
        num_paragraphs = len(h.correct_matches)
        selected_paragraphs = paragraphs[:num_paragraphs] if len(paragraphs) >= num_paragraphs else paragraphs
        
        # Xáo trộn headings
        shuffled_headings = h.headings.copy()
        random.shuffle(shuffled_headings)
        
        heading_responses.append(HeadingMatchingResponse(
            order=h.order,
            headings=shuffled_headings,
            paragraphs=selected_paragraphs
        )) 
    # Format fill blanks
    fill_blank_responses = []
    for fb in fill_blanks:
        # Tạo placeholder cho blanks trong passage_text
        passage_text_with_placeholder = fb.passage_text
        blank_ids = []
        for blank in fb.blanks:
            blank_id = blank["blank_id"]
            blank_ids.append(blank_id)
            # Thay thế [blank_id] bằng [___] để hiển thị
            passage_text_with_placeholder = passage_text_with_placeholder.replace(
                f"[{blank_id}]", "[________]"
            )
        
        fill_blank_responses.append(FillBlankResponse(
            order=fb.order,
            passage_text=passage_text_with_placeholder,
            blanks=blank_ids,
            case_sensitive=fb.case_sensitive
        ))
    tfng_responses = []
    for tf in true_false_not_given:
        statements = [item["statement"] for item in tf.statements]
        # Có thể xáo trộn thứ tự statements nếu muốn
        # random.shuffle(statements)
        
        tfng_responses.append(TrueFalseNotGivenResponse(
            order=tf.order,
            statements=statements
        ))
    # 5. Trả về response
    return ReadingSessionStartResponse(
        session_id=str(session.id),  # Tạm thời dùng passage_id làm session_id
        title=passage.title,
        content=passage.content,
        image_url=passage.image_url,
        learning_tip=passage.learning_tip,
        completed_questions=0,
        total_questions=passage.total_questions,
        time_remaining_seconds=passage.time_limit_minutes * 60,
        multiple_choices=[
            MultipleChoiceResponse(
                id=str(m.id),
                order=m.order,
                question_text=m.question_text,
                options=m.options
            ) for m in multiple_choices
        ],
        heading_matchings=heading_responses, 
        fill_blanks=fill_blank_responses , 
        true_false_not_given=tfng_responses
    )

@router.patch(path="/sessions/{session_id}/draft")
async def save_reading_draft(session_id: str, payload: ReadingDraftRequest):
    """Lưu nháp bài đọc khi user đang làm dở"""
     # Lấy session từ database
    session = await UserReadingSessionModel.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Cập nhật session
    session.time_remaining_seconds = payload.time_remaining_seconds
    session.user_answers = payload.user_answers
    
    # Tính số câu đã làm
    completed = len(payload.user_answers)
    session.completed_questions = min(completed, session.total_questions)
    
    session.updated_at = datetime.now(UTC)
    await session.save()
    
    return {
        "success": True,
        "message": "Draft saved successfully",
        "session_id": session_id,
        "completed_questions": session.completed_questions,
        "total_questions": session.total_questions
    }

@router.post(path="/sessions/{session_id}/submit")
async def submit_reading_answers(session_id: str, payload: dict):
    """Chấm điểm bài đọc và trả về kết quả"""
    # Lấy session
    session = await UserReadingSessionModel.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_answers = payload.get("user_answers", {})  # ← Lấy từ dict
    time_remaining = payload.get("time_remaining_seconds", 0)
    # Lấy passage và các câu hỏi
    passage = await session.passage_id.fetch()
    
    # Lấy tất cả câu hỏi
    multiple_choices = await ReadingMultipleChoiceModel.find(
        ReadingMultipleChoiceModel.passage_id.id == passage.id
    ).to_list()
    
    heading_matchings = await ReadingHeadingMatchingModel.find(
        ReadingHeadingMatchingModel.passage_id.id == passage.id
    ).to_list()
    
    fill_blanks = await ReadingFillBlankModel.find(
        ReadingFillBlankModel.passage_id.id == passage.id
    ).to_list()
    true_false_not_given = await ReadingTrueFalseNotGivenModel.find(
        ReadingTrueFalseNotGivenModel.passage_id.id == passage.id
    ).to_list()
    # Khởi tạo kết quả
    detailed_results = {}
    score = 0
    total_questions = 0
    
    # 1. Chấm Multiple Choice
    for mc in multiple_choices:
        total_questions += 1
        question_id = str(mc.id)
        user_answer = user_answers.get(question_id, "")
        is_correct = user_answer == mc.correct_answer
        if is_correct:
            score += 1
        detailed_results[question_id] = QuestionResult(
            is_correct=is_correct,
            user_answer=user_answer,
            correct_answer=mc.correct_answer
        )
    
    # 3. Chấm Heading Matching
    for hm in heading_matchings:
        total_questions += len(hm.correct_matches)
        for paragraph_id, correct_heading in hm.correct_matches.items():
            user_answer = user_answers.get(paragraph_id, "")
            is_correct = user_answer == correct_heading
            if is_correct:
                score += 1
            detailed_results[paragraph_id] = QuestionResult(
                is_correct=is_correct,
                user_answer=user_answer,
                correct_answer=correct_heading
            )
    
    # 4. Chấm Fill-in-the-blank
    for fb in fill_blanks:
        total_questions += len(fb.blanks)
        for blank in fb.blanks:
            blank_id = blank["blank_id"]
            correct_answer = blank["correct_answer"]
            user_answer = user_answers.get(blank_id, "")
            
            if fb.case_sensitive:
                is_correct = user_answer == correct_answer
            else:
                is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
            
            if is_correct:
                score += 1
            
            detailed_results[blank_id] = QuestionResult(
                is_correct=is_correct,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
    for tf in true_false_not_given:
        for item in tf.statements:
            total_questions += 1
            statement_id = f"tf_{tf.order}_{tf.statements.index(item)}"  # Tạo ID duy nhất
            # Hoặc dùng index: statement_id = f"statement_{tf.statements.index(item)}"
            
            correct_answer = item["correct_answer"].upper()  # TRUE/FALSE/NOT GIVEN
            user_answer = user_answers.get(statement_id, "").upper()
            
            is_correct = user_answer == correct_answer
            if is_correct:
                score += 1
            
            detailed_results[statement_id] = {
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "statement": item["statement"]  # Thêm để frontend biết câu nào
            }
    
    # Cập nhật session
    session.score = score
    session.status = "COMPLETED"
    session.user_answers = user_answers
    session.completed_questions = total_questions
    session.time_remaining_seconds = time_remaining
    session.updated_at = datetime.now(UTC)
    await session.save()
    
    # Tính accuracy
    accuracy_rate = (score / total_questions) * 100 if total_questions > 0 else 0
    
    return ReadingSubmitResponse(
        status="COMPLETED",
        score=score,
        total_questions=total_questions,
        accuracy_rate=round(accuracy_rate, 2),
        detailed_results=detailed_results
    )