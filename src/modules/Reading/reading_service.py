import logging
import random
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple
from beanie import PydanticObjectId

logger = logging.getLogger("omni_english")

from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel,
    ReadingVocabularyBookmarkModel
)
from .Reading_dto import (
    ReadingSessionStartResponse,
    MultipleChoiceResponse,
    HeadingMatchingResponse,
    FillBlankResponse,
    TrueFalseNotGivenResponse,
    ReadingSubmitResponse,
    QuestionResult,
    ReadingSessionDetailResponse,
    PassageSummaryResponse,
    PassageListResponse,
    PassageDetailResponse,
    UserHistoryItemResponse,
    UserHistoryListResponse,
    UserReadingStatsResponse,
    ReadingSessionReviewResponse,
    ReadingVocabularyBookmarkResponse
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
                correct_answer=mc.correct_answer,
                statement=mc.question_text,
                options=mc.options,
                explanation=mc.explanation,
                excerpt=mc.excerpt
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
                    correct_answer=correct_heading,
                    statement=f"Heading selection for paragraph {paragraph_id.replace('paragraph_', '').replace('_', ' ').strip().capitalize()}",
                    explanation=hm.explanations.get(paragraph_id) if hm.explanations else None,
                    excerpt=hm.excerpts.get(paragraph_id) if hm.excerpts else None
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
                    correct_answer=correct_answer,
                    statement=f"Sentence completion blank {blank_id.replace('blank_', '')}",
                    explanation=blank.get("explanation"),
                    excerpt=blank.get("excerpt")
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
                    correct_answer=correct_answer,
                    statement=item["statement"],
                    options=["TRUE", "FALSE", "NOT GIVEN"],
                    explanation=item.get("explanation"),
                    excerpt=item.get("excerpt")
                )
        
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

    @staticmethod
    async def get_session_details(session_id: str) -> ReadingSessionDetailResponse:
        """5. Lấy toàn bộ thông tin session"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        passage = await session.passage_id.fetch()
        return ReadingSessionDetailResponse(
            session_id=str(session.id),
            user_id=session.user_id,
            passage_id=str(passage.id) if passage else "",
            passage_title=passage.title if passage else None,
            completed_questions=session.completed_questions,
            total_questions=session.total_questions,
            time_remaining_seconds=session.time_remaining_seconds,
            score=session.score,
            status=session.status,
            user_answers=session.user_answers,
            start_at=session.start_at.isoformat() if session.start_at else None,
            updated_at=session.updated_at.isoformat() if session.updated_at else None
        )

    @staticmethod
    async def get_passages(
        page: int = 1,
        limit: int = 10,
        level: Optional[str] = None,
        topic: Optional[str] = None,
        question_type: Optional[str] = None
    ) -> PassageListResponse:
        """6. Lấy danh sách các bài đọc có sẵn (phân trang)"""
        passage_ids = None
        if question_type:
            if question_type == "Multiple Choice":
                records = await ReadingMultipleChoiceModel.find().to_list()
                passage_ids = {r.passage_id.id for r in records}
            elif question_type == "Heading Matching":
                records = await ReadingHeadingMatchingModel.find().to_list()
                passage_ids = {r.passage_id.id for r in records}
            elif question_type == "Fill Blank":
                records = await ReadingFillBlankModel.find().to_list()
                passage_ids = {r.passage_id.id for r in records}
            elif question_type == "T/F/NG":
                records = await ReadingTrueFalseNotGivenModel.find().to_list()
                passage_ids = {r.passage_id.id for r in records}
            else:
                passage_ids = set()

        query = ReadingPassageModel.find()
        if passage_ids is not None:
            query = query.find({"_id": {"$in": list(passage_ids)}})
        if topic:
            query = query.find({"topic": {"$regex": topic, "$options": "i"}})
        
        total = await query.count()
        skip = (page - 1) * limit
        passages = await query.sort("-created_at").skip(skip).limit(limit).to_list()
        
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        items = []
        for p in passages:
            q_types = []
            if await ReadingMultipleChoiceModel.find(ReadingMultipleChoiceModel.passage_id.id == p.id).count() > 0:
                q_types.append("Multiple Choice")
            if await ReadingHeadingMatchingModel.find(ReadingHeadingMatchingModel.passage_id.id == p.id).count() > 0:
                q_types.append("Heading Matching")
            if await ReadingFillBlankModel.find(ReadingFillBlankModel.passage_id.id == p.id).count() > 0:
                q_types.append("Fill Blank")
            if await ReadingTrueFalseNotGivenModel.find(ReadingTrueFalseNotGivenModel.passage_id.id == p.id).count() > 0:
                q_types.append("T/F/NG")

            items.append(
                PassageSummaryResponse(
                    id=str(p.id),
                    title=p.title,
                    topic=p.topic,
                    time_limit_minutes=p.time_limit_minutes,
                    total_questions=p.total_questions,
                    image_url=p.image_url,
                    learning_tip=p.learning_tip,
                    created_at=p.created_at.isoformat() if p.created_at else None,
                    question_types=q_types
                )
            )
        return PassageListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    @staticmethod
    async def get_passage_detail(passage_id: str) -> PassageDetailResponse:
        """7. Lấy thông tin chi tiết của một passage"""
        passage = await ReadingPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        return PassageDetailResponse(
            id=str(passage.id),
            title=passage.title,
            topic=passage.topic,
            content=passage.content,
            image_url=passage.image_url,
            time_limit_minutes=passage.time_limit_minutes,
            total_questions=passage.total_questions,
            learning_tip=passage.learning_tip,
            created_at=passage.created_at.isoformat() if passage.created_at else None
        )

    @staticmethod
    async def get_user_history(
        user_id: str,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None
    ) -> UserHistoryListResponse:
        """8. Lấy danh sách các bài đọc user đã làm"""
        query = UserReadingSessionModel.find(UserReadingSessionModel.user_id == user_id)
        if status:
            query = query.find(UserReadingSessionModel.status == status)
        
        total = await query.count()
        skip = (page - 1) * limit
        sessions = await query.sort("-updated_at").skip(skip).limit(limit).to_list()
        
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        items = []
        for s in sessions:
            passage = await s.passage_id.fetch()
            has_passage = passage and hasattr(passage, "id")
            accuracy_rate = (s.score / s.total_questions * 100) if s.total_questions > 0 else 0
            items.append(UserHistoryItemResponse(
                session_id=str(s.id),
                passage_id=str(passage.id) if has_passage else "",
                passage_title=passage.title if has_passage and hasattr(passage, "title") else "Unknown Passage",
                score=s.score,
                total_questions=s.total_questions,
                accuracy_rate=round(accuracy_rate, 2),
                status=s.status,
                attempt_number=s.attempt_number,
                completed_questions=s.completed_questions,
                start_at=s.start_at.isoformat() if s.start_at else None,
                updated_at=s.updated_at.isoformat() if s.updated_at else None
            ))
        
        return UserHistoryListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    @staticmethod
    async def delete_session(session_id: str) -> Dict:
        """9. Hủy session đang làm dở"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        await session.delete()
        return {
            "success": True,
            "message": "Session deleted successfully",
            "session_id": session_id
        }

    @staticmethod
    async def get_user_stats(user_id: str) -> UserReadingStatsResponse:
        """10. Thống kê tổng quan của user"""
        completed_sessions = await UserReadingSessionModel.find(
            UserReadingSessionModel.user_id == user_id,
            UserReadingSessionModel.status == "COMPLETED"
        ).to_list()
        
        total_completed = len(completed_sessions)
        if total_completed == 0:
            return UserReadingStatsResponse(
                total_sessions_completed=0,
                average_accuracy_rate=0.0,
                highest_score=0,
                lowest_score=0,
                skills_to_improve=["Vocabulary Matching", "Multiple Choice", "True/False/Not Given"],
                total_xp=0
            )
        
        scores = [s.score for s in completed_sessions]
        accuracies = [(s.score / s.total_questions * 100) if s.total_questions > 0 else 0 for s in completed_sessions]
        avg_acc = sum(accuracies) / total_completed
        highest = max(scores)
        lowest = min(scores)
        total_xp = sum(scores) * 10
        
        skills_to_improve = []
        if avg_acc < 80:
            skills_to_improve.append("Multiple Choice")
        if avg_acc < 70:
            skills_to_improve.append("True/False/Not Given")
        if not skills_to_improve:
            skills_to_improve = ["Advanced Vocabulary Matching"]
        
        return UserReadingStatsResponse(
            total_sessions_completed=total_completed,
            average_accuracy_rate=round(avg_acc, 2),
            highest_score=highest,
            lowest_score=lowest,
            skills_to_improve=skills_to_improve,
            total_xp=total_xp
        )

    @staticmethod
    async def get_session_review(session_id: str) -> ReadingSessionReviewResponse:
        """11. Review bài đã làm"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        passage = await session.passage_id.fetch()
        
        res = await ReadingService.submit_answers(
            session_id=session_id,
            user_answers=session.user_answers,
            time_remaining=session.time_remaining_seconds
        )
        
        return ReadingSessionReviewResponse(
            session_id=str(session.id),
            passage_id=str(passage.id) if passage else "",
            passage_title=passage.title if passage else "",
            passage_content=passage.content if passage else "",
            score=res.score,
            total_questions=res.total_questions,
            accuracy_rate=res.accuracy_rate,
            status=session.status,
            detailed_results=res.detailed_results
        )

    @staticmethod
    async def bookmark_vocabulary(
        session_id: str,
        word: str,
        context: Optional[str] = None
    ) -> ReadingVocabularyBookmarkResponse:
        """12. Bookmark/Nổi bật từ vựng"""
        session = await UserReadingSessionModel.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        bookmark = ReadingVocabularyBookmarkModel(
            user_id=session.user_id,
            session_id=session_id,
            word=word,
            context=context
        )
        await bookmark.insert()
        
        return ReadingVocabularyBookmarkResponse(
            success=True,
            message="Vocabulary bookmarked successfully",
            id=str(bookmark.id),
            session_id=session_id,
            word=word,
            context=context,
            created_at=bookmark.created_at.isoformat() if bookmark.created_at else None
        )
