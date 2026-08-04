import random
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple
from beanie import PydanticObjectId

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
    ReadingSubmitResponse,
    QuestionResult
)


class ReadingService:
    
    @staticmethod
    async def get_passage(passage_id: str) -> ReadingPassageModel:
        """Lấy passage theo ID"""
        passage = await ReadingPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        return passage
    
    @staticmethod
    async def get_or_create_session(
        user_id: str, 
        passage_id: str
    ) -> UserReadingSessionModel:
        """Lấy session đang làm dở hoặc tạo mới"""
        passage = await ReadingPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        
        # Tìm session đang làm dở
        existing_session = await UserReadingSessionModel.find_one(
            UserReadingSessionModel.user_id == user_id,
            UserReadingSessionModel.passage_id.id == PydanticObjectId(passage_id),
            UserReadingSessionModel.status == "IN_PROGRESS"
        )
        
        if existing_session:
            return existing_session
        
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
        return session
    
    @staticmethod
    async def get_session(session_id: str) -> UserReadingSessionModel:
        """Lấy session theo ID"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        return session
    
    @staticmethod
    async def format_multiple_choices(
        passage_id: str
    ) -> List[MultipleChoiceResponse]:
        """Format multiple choice questions"""
        multiple_choices = await ReadingMultipleChoiceModel.find(
            ReadingMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        return [
            MultipleChoiceResponse(
                id=str(m.id),
                order=m.order,
                question_text=m.question_text,
                options=m.options
            ) for m in multiple_choices
        ]
    
    @staticmethod
    async def format_heading_matchings(
        passage: ReadingPassageModel,
        passage_id: str
    ) -> List[HeadingMatchingResponse]:
        """Format heading matching questions"""
        heading_matchings = await ReadingHeadingMatchingModel.find(
            ReadingHeadingMatchingModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        heading_responses = []
        for h in heading_matchings:
            paragraphs = [p.strip() for p in passage.content.split('\n\n') if p.strip()]
            num_paragraphs = len(h.correct_matches)
            selected_paragraphs = paragraphs[:num_paragraphs] if len(paragraphs) >= num_paragraphs else paragraphs
            
            shuffled_headings = h.headings.copy()
            random.shuffle(shuffled_headings)
            
            heading_responses.append(HeadingMatchingResponse(
                order=h.order,
                headings=shuffled_headings,
                paragraphs=selected_paragraphs
            ))
        
        return heading_responses
    
    @staticmethod
    async def format_fill_blanks(passage_id: str) -> List[FillBlankResponse]:
        """Format fill-in-the-blank questions"""
        fill_blanks = await ReadingFillBlankModel.find(
            ReadingFillBlankModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        fill_blank_responses = []
        for fb in fill_blanks:
            passage_text_with_placeholder = fb.passage_text
            blank_ids = []
            for blank in fb.blanks:
                blank_id = blank["blank_id"]
                blank_ids.append(blank_id)
                passage_text_with_placeholder = passage_text_with_placeholder.replace(
                    f"[{blank_id}]", "[________]"
                )
            
            fill_blank_responses.append(FillBlankResponse(
                order=fb.order,
                passage_text=passage_text_with_placeholder,
                blanks=blank_ids,
                case_sensitive=fb.case_sensitive
            ))
        
        return fill_blank_responses
    
    @staticmethod
    async def format_true_false_not_given(
        passage_id: str
    ) -> List[TrueFalseNotGivenResponse]:
        """Format True/False/Not Given questions"""
        true_false_not_given = await ReadingTrueFalseNotGivenModel.find(
            ReadingTrueFalseNotGivenModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        tfng_responses = []
        for tf in true_false_not_given:
            statements = [item["statement"] for item in tf.statements]
            tfng_responses.append(TrueFalseNotGivenResponse(
                order=tf.order,
                statements=statements
            ))
        
        return tfng_responses
    
    @staticmethod
    async def save_draft(
        session_id: str,
        time_remaining_seconds: int,
        user_answers: Dict[str, str]
    ) -> Dict:
        """Lưu nháp bài làm"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        session.time_remaining_seconds = time_remaining_seconds
        session.user_answers = user_answers
        session.completed_questions = min(len(user_answers), session.total_questions)
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        return {
            "success": True,
            "message": "Draft saved successfully",
            "session_id": session_id,
            "completed_questions": session.completed_questions,
            "total_questions": session.total_questions,
            "user_answers": session.user_answers,
            "time_remaining_seconds": session.time_remaining_seconds
        }
    
    @staticmethod
    async def get_draft(session_id: str) -> Dict:
        """Lấy nháp bài làm đã lưu"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        passage = await session.passage_id.fetch()
        return {
            "success": True,
            "session_id": str(session.id),
            "user_id": session.user_id,
            "passage_id": str(passage.id),
            "status": session.status,
            "completed_questions": session.completed_questions,
            "total_questions": session.total_questions,
            "time_remaining_seconds": session.time_remaining_seconds,
            "user_answers": session.user_answers,
            "score": session.score,
            "start_at": session.start_at,
            "updated_at": session.updated_at
        }
    
    @staticmethod
    async def submit_answers(
        session_id: str,
        user_answers: Dict[str, str],
        time_remaining: int
    ) -> ReadingSubmitResponse:
        """Chấm điểm và lưu kết quả"""
        # Lấy session
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Lấy passage
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
        
        # 2. Chấm Heading Matching
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
        
        # 3. Chấm Fill-in-the-blank
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
        
        # 4. Chấm True/False/Not Given
        for tf in true_false_not_given:
            for idx, item in enumerate(tf.statements):
                total_questions += 1
                statement_id = f"tf_{tf.order}_{idx}"
                correct_answer = item["correct_answer"].upper()
                user_answer = user_answers.get(statement_id, "").upper()
                
                is_correct = user_answer == correct_answer
                if is_correct:
                    score += 1
                
                detailed_results[statement_id] = QuestionResult(
                    is_correct=is_correct,
                    user_answer=user_answer,
                    correct_answer=correct_answer
                )
                # Thêm statement để frontend biết
                detailed_results[statement_id].statement = item["statement"]
        
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