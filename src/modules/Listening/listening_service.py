# modules/Listening/listening_service.py

import random
from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import PydanticObjectId

from models.Listening import (
    ListeningPassageModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)
from .listening_dto import (
    TranscriptLine,
    KeyVocabularyItem,
    ListeningMultipleChoiceResponse,
    ListeningCompletionResponse,
    ListeningSubmitResponse,
    QuestionReviewDetail,
    TranscriptComparisonWord
)


class ListeningService:

    @staticmethod
    async def _get_session_by_id(session_id: str) -> Optional[UserListeningSessionModel]:
        """Lấy session theo ID, hỗ trợ cả ObjectId và chuỗi."""
        if not session_id:
            return None

        try:
            session = await UserListeningSessionModel.get(PydanticObjectId(session_id))
            if session:
                return session
        except Exception:
            pass

        return await UserListeningSessionModel.get(session_id)
    
    @staticmethod
    async def get_passage(passage_id: str) -> ListeningPassageModel:
        """Lấy passage theo ID"""
        passage = await ListeningPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        return passage
    @staticmethod
    async def get_session(session_id: str) -> UserListeningSessionModel:
        """Lấy session theo ID"""
        session = await ListeningService._get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        return session
    @staticmethod
    async def get_or_create_session(
        user_id: str,
        passage_id: str,
        session_type: str = "COMPREHENSION"
    ) -> UserListeningSessionModel:
        """Lấy session đang làm dở hoặc tạo mới"""
        passage = await ListeningPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        
        # Tìm session đang làm dở
        existing_session = await UserListeningSessionModel.find_one(
            UserListeningSessionModel.user_id == user_id,
            UserListeningSessionModel.passage_id.id == PydanticObjectId(passage_id),
            UserListeningSessionModel.session_type == session_type,
            UserListeningSessionModel.status == "IN_PROGRESS"
        )
        
        if existing_session:
            return existing_session
        
        # Tạo session mới
        session = UserListeningSessionModel(
            user_id=user_id,
            passage_id=passage,
            session_type=session_type,
            completed_questions=0,
            time_remaining_seconds=passage.time_limit_minutes * 60,
            status="IN_PROGRESS"
        )
        await session.save()
        return session
    @staticmethod
    async def get_draft(session_id: str) -> Dict:
        """Lấy nháp bài listening đã lưu"""
        session = await ListeningService.get_session(session_id)  # Dùng static method
        
        # Lấy passage
        passage = await session.passage_id.fetch()
        
        if session.session_type == "COMPREHENSION":
            return {
                "success": True,
                "session_id": str(session.id),
                "user_id": session.user_id,
                "passage_id": str(passage.id),
                "passage_title": passage.title,
                "session_type": session.session_type,
                "status": session.status,
                "user_answers": session.user_answers or {},
                "time_remaining_seconds": session.time_remaining_seconds or 0,
                "completed_questions": session.completed_questions or 0,
                "total_questions": passage.total_questions,
                "score": session.score,
                "start_at": session.start_at,
                "updated_at": session.updated_at
            }
        else:  # DICTATION
            return {
                "success": True,
                "session_id": str(session.id),
                "user_id": session.user_id,
                "passage_id": str(passage.id),
                "passage_title": passage.title,
                "session_type": session.session_type,
                "status": session.status,
                "user_typed_text": session.user_typed_text or "",
                "words_typed": session.words_typed or 0,
                "wpm": session.wpm or 0,
                "score": session.accuracy_rate,
                "total_questions": passage.total_questions,
                "start_at": session.start_at,
                "updated_at": session.updated_at
            }

    @staticmethod
    async def format_transcript(passage: ListeningPassageModel) -> List[TranscriptLine]:
        """Format interactive transcript"""
        return [
            TranscriptLine(
                start_time=item.get("start_time", ""),
                end_time=item.get("end_time", ""),
                en=item.get("en", ""),
                vi=item.get("vi", "")
            )
            for item in passage.interactive_transcript
        ]
    
    @staticmethod
    async def format_vocabulary(passage: ListeningPassageModel) -> List[KeyVocabularyItem]:
        """Format key vocabulary"""
        return [
            KeyVocabularyItem(
                word=item.get("word", ""),
                meaning=item.get("meaning", "")
            )
            for item in passage.key_vocabulary
        ]
    
    @staticmethod
    async def format_multiple_choices(
        passage_id: str
    ) -> List[ListeningMultipleChoiceResponse]:
        """Format multiple choice questions (hide correct answers)"""
        multiple_choices = await ListeningMultipleChoiceModel.find(
            ListeningMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        # Xáo trộn thứ tự options để tránh học thuộc đáp án
        for mc in multiple_choices:
            random.shuffle(mc.options)
        
        return [
            ListeningMultipleChoiceResponse(
                id=str(m.id),
                order=m.order,
                question_text=m.question_text,
                options=m.options
            ) for m in multiple_choices
        ]
    
    @staticmethod
    async def format_completions(
        passage_id: str
    ) -> List[ListeningCompletionResponse]:
        """Format completion questions"""
        completions = await ListeningCompletionModel.find(
            ListeningCompletionModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        return [
            ListeningCompletionResponse(
                id=str(c.id),
                order=c.order,
                template_text=c.template_text,
                case_sensitive=c.case_sensitive
            ) for c in completions
        ]
    
    @staticmethod
    async def save_comprehension_draft(
        session_id: str,
        user_answers: Dict[str, str],
        time_remaining_seconds: int
    ) -> Dict:
        """Lưu nháp comprehension"""
        session = await ListeningService._get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        passage = await session.passage_id.fetch()
        session.user_answers = user_answers
        session.time_remaining_seconds = time_remaining_seconds
        session.completed_questions = min(len(user_answers), passage.total_questions)
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        return {
            "success": True,
            "message": "Comprehension draft saved successfully",
            "session_id": session_id,
            "status": "IN_PROGRESS",
            "completed_questions": session.completed_questions
        }
    
    @staticmethod
    async def save_dictation_draft(
        session_id: str,
        user_typed_text: str
    ) -> Dict:
        """Lưu nháp dictation"""
        session = await ListeningService._get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        
        session.user_typed_text = user_typed_text
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        return {
            "success": True,
            "message": "Dictation draft saved successfully",
            "session_id": session_id,
            "status": "IN_PROGRESS"
        }
    
    @staticmethod
    async def grade_comprehension(
        session_id: str,
        user_answers: Dict[str, str]
    ) -> ListeningSubmitResponse:
        """Chấm điểm comprehension với auto-grading"""
        # Lấy session
        session = await ListeningService._get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Fetch passage
        passage = await session.passage_id.fetch()
        passage_id = passage.id
        
        # Lấy tất cả câu hỏi
        multiple_choices = await ListeningMultipleChoiceModel.find(
            ListeningMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        completions = await ListeningCompletionModel.find(
            ListeningCompletionModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        # Khởi tạo kết quả
        detailed_review = []
        competency_matrix = {
            "Global Understanding": 0,
            "Specific Information Retrieval": 0,
            "Inference & Tone": 0,
            "Vocabulary": 0
        }
        competency_counts = {
            "Global Understanding": 0,
            "Specific Information Retrieval": 0,
            "Inference & Tone": 0,
            "Vocabulary": 0
        }
        
        correct_count = 0
        total_questions = len(multiple_choices) + sum(
            len(c.correct_answers) for c in completions
        )
        
        # 1. Chấm Multiple Choice
        for mc in multiple_choices:
            question_id = str(mc.id)
            user_answer = user_answers.get(question_id, "")
            is_correct = user_answer == mc.correct_answer

            if is_correct:
                correct_count += 1

            comp_type = mc.competency_type or "Global Understanding"
            if comp_type in competency_counts:
                competency_counts[comp_type] += 1
                if is_correct:
                    competency_matrix[comp_type] += 1

            detailed_review.append(QuestionReviewDetail(
                question_text=mc.question_text,
                your_answer=user_answer or "Not answered",
                correct_answer=mc.correct_answer,
                is_correct=is_correct,
                timestamp_clip=mc.timestamp_clip,
                learning_hint=mc.learning_hint or ListeningService._get_default_hint(is_correct)
            ))

        # 2. Chấm Completion
        for comp in completions:
            for gap_id, correct_answer in comp.correct_answers.items():
                user_answer = user_answers.get(gap_id, "")

                if comp.case_sensitive:
                    is_correct = user_answer == correct_answer
                else:
                    is_correct = user_answer.lower().strip() == correct_answer.lower().strip()

                if is_correct:
                    correct_count += 1

                comp_type = "Specific Information Retrieval"
                if comp_type in competency_counts:
                    competency_counts[comp_type] += 1
                    if is_correct:
                        competency_matrix[comp_type] += 1

                detailed_review.append(QuestionReviewDetail(
                    question_text=f"Fill in the blank: {comp.template_text.replace(f'[{gap_id}]', '_____')}",
                    your_answer=user_answer or "Not answered",
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                    timestamp_clip=None,
                    learning_hint="Review the audio segment to find the missing word."
                ))

        # Tính tỷ lệ phần trăm cho competency matrix
        for comp_type in competency_matrix:
            if competency_counts[comp_type] > 0:
                competency_matrix[comp_type] = round(
                    (competency_matrix[comp_type] / competency_counts[comp_type]) * 100, 2
                )

        # Tính accuracy
        accuracy_rate = (correct_count / total_questions) * 100 if total_questions > 0 else 0

        # Cập nhật session
        session.accuracy_rate = round(accuracy_rate, 2)
        session.score_summary = f"{correct_count} out of {total_questions} Correct"
        session.xp_earned = ListeningService._calculate_xp(accuracy_rate, total_questions)
        session.competency_matrix = competency_matrix
        session.detailed_question_review = [r.dict() for r in detailed_review]
        session.completed_questions = total_questions
        session.user_answers = user_answers
        session.time_remaining_seconds = 0
        session.status = "COMPLETED"
        session.score = correct_count
        session.updated_at = datetime.now(UTC)
        await session.save()

        return ListeningSubmitResponse(
            session_id=session_id,
            session_type="COMPREHENSION",
            status="COMPLETED",
            accuracy_rate=round(accuracy_rate, 2),
            score_summary=session.score_summary,
            xp_earned=session.xp_earned,
            competency_matrix=competency_matrix,
            detailed_question_review=detailed_review,
            words_typed=0,
            wpm=0,
            missed_contractions=0,
            transcript_comparison=[],
            spelling_tip=None,
            listening_insight=None
        )
    
    @staticmethod
    async def grade_dictation(
        session_id: str,
        user_typed_text: str
    ) -> ListeningSubmitResponse:
        """Chấm điểm dictation với so sánh từng từ"""
        # Lấy session
        session = await ListeningService._get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Fetch passage
        passage = await session.passage_id.fetch()
        
        # Lấy transcript gốc (full text từ interactive_transcript)
        original_transcript = " ".join([
            item.get("en", "") for item in passage.interactive_transcript
        ])
        
        # Tách từ và so sánh
        original_words = original_transcript.split()
        user_words = user_typed_text.split() if user_typed_text else []
        
        # So sánh từng từ
        transcript_comparison = []
        correct_words = 0
        missed_contractions = 0
        
        # Danh sách contractions để kiểm tra
        contractions = ["don't", "doesn't", "didn't", "can't", "won't", "shouldn't", 
                       "wouldn't", "couldn't", "haven't", "hasn't", "hadn't", "isn't",
                       "aren't", "weren't", "wasn't", "i'm", "you're", "he's", "she's",
                       "it's", "we're", "they're", "i've", "you've", "we've", "they've"]
        
        for i, original_word in enumerate(original_words):
            user_word = user_words[i] if i < len(user_words) else None
            is_correct = user_word == original_word if user_word else False
            
            if is_correct:
                correct_words += 1
            
            # Kiểm tra missed contractions
            if original_word.lower() in contractions and not user_word:
                missed_contractions += 1
            
            transcript_comparison.append(TranscriptComparisonWord(
                word=original_word,
                user_word=user_word,
                is_correct=is_correct
            ))
        
        # Tính WPM (Words Per Minute)
        # Giả sử average listening time = 1 phút cho 100 từ
        wpm = int(correct_words / 1) if correct_words > 0 else 0
        
        # Tính accuracy
        accuracy_rate = (correct_words / len(original_words)) * 100 if original_words else 0
        
        # Tạo tips
        spelling_tip = ListeningService._get_spelling_tip(accuracy_rate, missed_contractions)
        listening_insight = ListeningService._get_listening_insight(accuracy_rate)
        
        # Tính XP
        xp_earned = ListeningService._calculate_xp(accuracy_rate, len(original_words))
        
        # Cập nhật session
        session.accuracy_rate = round(accuracy_rate, 2)
        session.score_summary = f"{correct_words} out of {len(original_words)} words correct"
        session.xp_earned = xp_earned
        session.words_typed = len(user_words)
        session.wpm = wpm
        session.missed_contractions = missed_contractions
        session.transcript_comparison = [t.dict() for t in transcript_comparison]
        session.spelling_tip = spelling_tip
        session.listening_insight = listening_insight
        session.status = "COMPLETED"
        session.score = correct_count
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        return ListeningSubmitResponse(
            session_id=session_id,
            session_type="DICTATION",
            status="COMPLETED",
            accuracy_rate=round(accuracy_rate, 2),
            score_summary=session.score_summary,
            xp_earned=xp_earned,
            competency_matrix={},
            detailed_question_review=[],
            words_typed=len(user_words),
            wpm=wpm,
            missed_contractions=missed_contractions,
            transcript_comparison=transcript_comparison,
            spelling_tip=spelling_tip,
            listening_insight=listening_insight
        )
    
    @staticmethod
    def _get_default_hint(is_correct: bool) -> str:
        """Lấy hint mặc định"""
        if is_correct:
            return "✅ Well done! This answer is correct."
        return "❌ Incorrect. Review the audio again and try to understand the context."
    
    @staticmethod
    def _calculate_xp(accuracy_rate: float, total_questions: int) -> int:
        """Tính XP dựa trên accuracy và số câu hỏi"""
        base_xp = total_questions * 10
        bonus_xp = 0
        
        if accuracy_rate >= 90:
            bonus_xp = base_xp * 0.5  # 50% bonus
        elif accuracy_rate >= 70:
            bonus_xp = base_xp * 0.2  # 20% bonus
        
        return int(base_xp + bonus_xp)
    
    @staticmethod
    def _get_spelling_tip(accuracy_rate: float, missed_contractions: int) -> str:
        """Tạo spelling tip dựa trên kết quả"""
        tips = []
        
        if accuracy_rate < 60:
            tips.append("📝 Try listening to the audio again and focus on each word.")
        
        if missed_contractions > 3:
            tips.append("🔍 Pay attention to contractions like 'don't', 'can't' - they're common in spoken English.")
        
        if 60 <= accuracy_rate < 80:
            tips.append("👂 Practice with slower speed or use the interactive transcript to check difficult words.")
        
        if accuracy_rate >= 80:
            tips.append("🌟 Great work! Your spelling is strong. Try to improve your typing speed.")
        
        return " ".join(tips) if tips else "💪 Keep practicing to improve your dictation skills!"
    
    @staticmethod
    def _get_listening_insight(accuracy_rate: float) -> str:
        """Tạo listening insight"""
        if accuracy_rate >= 90:
            return "🎉 Excellent listening comprehension! You've mastered this audio."
        elif accuracy_rate >= 70:
            return "📈 Good job! You understand most of the content. Try to identify specific details next time."
        elif accuracy_rate >= 50:
            return "📚 Fair effort. Consider listening multiple times and using the transcript to check difficult sections."
        else:
            return "🎯 Keep practicing! Start with slower audio and gradually increase speed. Focus on key vocabulary first."