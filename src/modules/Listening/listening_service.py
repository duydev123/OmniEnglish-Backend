# modules/Listening/listening_service.py

import random
from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import PydanticObjectId

from models.Listening import (
    ListeningPassageModel,
    ListeningAudioSegmentModel,
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
    TranscriptComparisonWord,
    ListeningPassageSummary,
    ListeningPassageListResponse
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
    async def list_passages(page: int = 1, limit: int = 10, question_type: Optional[str] = None):
        """Liệt kê passage listening có sẵn, hỗ trợ lọc theo question_type."""
        page = max(page, 1)
        limit = max(limit, 1)

        all_passages = await ListeningPassageModel.find_all().to_list()
        
        items = []
        for passage in all_passages:
            q_types = []
            if await ListeningMultipleChoiceModel.find(ListeningMultipleChoiceModel.passage_id.id == passage.id).count() > 0:
                q_types.append("Multiple Choice")
            if await ListeningCompletionModel.find(ListeningCompletionModel.passage_id.id == passage.id).count() > 0:
                q_types.append("Fill Blank")
            
            # Tất cả các bài nghe đều có thể làm chép chính tả (Dictation)
            q_types.append("Dictation")

            # Lọc theo question_type nếu có yêu cầu
            if question_type and question_type != "All":
                if question_type not in q_types:
                    continue

            items.append(
                ListeningPassageSummary(
                    id=str(passage.id),
                    title=passage.title,
                    unit_code=passage.unit_code,
                    audio_url=passage.audio_url,
                    time_limit_minutes=passage.time_limit_minutes,
                    total_questions=passage.total_questions,
                    question_types=q_types
                )
            )

        total = len(items)
        start = (page - 1) * limit
        end = start + limit
        page_items = items[start:end]

        return page_items, total

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
                options=m.options,
                timestamp_clip=m.timestamp_clip
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

            # Fetch audio segment
            audio_url = None
            start_time_ms = None
            end_time_ms = None
            segment_transcript = None
            if mc.audio_segment_id:
                try:
                    seg = await mc.audio_segment_id.fetch()
                    if seg:
                        audio_url = seg.audio_file_url or passage.audio_url
                        start_time_ms = seg.start_time_ms
                        end_time_ms = seg.end_time_ms
                        segment_transcript = seg.transcript
                except Exception:
                    pass

            detailed_review.append(QuestionReviewDetail(
                question_id=question_id,
                question_text=mc.question_text,
                your_answer=user_answer or "Not answered",
                correct_answer=mc.correct_answer,
                is_correct=is_correct,
                timestamp_clip=mc.timestamp_clip,
                learning_hint=mc.learning_hint or ListeningService._get_default_hint(is_correct),
                audio_url=audio_url,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                segment_transcript=segment_transcript
            ))

        # 2. Chấm Completion
        for comp in completions:
            # Fetch audio segment once per completion question block
            audio_url = None
            start_time_ms = None
            end_time_ms = None
            segment_transcript = None
            if comp.audio_segment_id:
                try:
                    seg = await comp.audio_segment_id.fetch()
                    if seg:
                        audio_url = seg.audio_file_url or passage.audio_url
                        start_time_ms = seg.start_time_ms
                        end_time_ms = seg.end_time_ms
                        segment_transcript = seg.transcript
                except Exception:
                    pass

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
                    question_id=str(comp.id),
                    question_text=f"Fill in the blank: {comp.template_text.replace(f'[{gap_id}]', '_____')}",
                    your_answer=user_answer or "Not answered",
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                    timestamp_clip=None,
                    learning_hint="Review the audio segment to find the missing word.",
                    audio_url=audio_url,
                    start_time_ms=start_time_ms,
                    end_time_ms=end_time_ms,
                    segment_transcript=segment_transcript
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
            listening_insight=None,
            audio_url=passage.audio_url,
            interactive_transcript=await ListeningService.format_transcript(passage)
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
            
            is_correct = False
            if user_word:
                import string
                clean_user = user_word.strip(string.punctuation).lower()
                clean_orig = original_word.strip(string.punctuation).lower()
                is_correct = clean_user == clean_orig
            
            if is_correct:
                correct_words += 1
            
            # Kiểm tra missed contractions
            if original_word.lower() in contractions and not user_word:
                missed_contractions += 1
            
            status = "correct" if is_correct else ("wrong" if user_word else "missing")
            
            transcript_comparison.append(TranscriptComparisonWord(
                word=original_word,
                user_word=user_word,
                is_correct=is_correct,
                status=status
            ))
        
        # Tính WPM (Words Per Minute) dựa trên thời gian thực tế
        elapsed_minutes = (session.updated_at - session.start_at).total_seconds() / 60.0 if session.start_at else 1.0
        if elapsed_minutes < 0.1:
            elapsed_minutes = 0.1
        wpm = int(correct_words / elapsed_minutes) if correct_words > 0 else 0
        
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
        session.score = correct_words
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
            listening_insight=listening_insight,
            audio_url=passage.audio_url,
            interactive_transcript=await ListeningService.format_transcript(passage)
        )
    
    @staticmethod
    async def get_user_history(
        user_id: str,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None
    ) -> Dict:
        """Lấy danh sách các bài nghe user đã làm hoặc nháp dở"""
        query = UserListeningSessionModel.find(UserListeningSessionModel.user_id == user_id)
        if status:
            query = query.find(UserListeningSessionModel.status == status)
        
        total = await query.count()
        skip = (page - 1) * limit
        sessions = await query.sort("-updated_at").skip(skip).limit(limit).to_list()
        
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        items = []
        for s in sessions:
            passage = await s.passage_id.fetch()
            has_passage = passage and hasattr(passage, "id")
            accuracy_rate = s.accuracy_rate
            items.append({
                "session_id": str(s.id),
                "passage_id": str(passage.id) if has_passage else "",
                "passage_title": passage.title if has_passage and hasattr(passage, "title") else "Unknown Passage",
                "score": int(s.score),
                "total_questions": passage.total_questions if has_passage and hasattr(passage, "total_questions") else s.completed_questions,
                "accuracy_rate": round(accuracy_rate, 2),
                "status": s.status,
                "session_type": s.session_type,
                "completed_questions": s.completed_questions,
                "start_at": s.start_at.isoformat() if s.start_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

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

    @staticmethod
    async def get_audio_segment_by_question(question_id: str):
        """Lấy audio segment và transcript segment theo question_id (hỗ trợ cả trắc nghiệm và điền ô trống)"""
        # Tìm trong Multiple Choice
        question = None
        try:
            question = await ListeningMultipleChoiceModel.get(PydanticObjectId(question_id))
        except Exception:
            pass

        if not question:
            try:
                question = await ListeningMultipleChoiceModel.get(question_id)
            except Exception:
                pass

        # Tìm trong Completion
        if not question:
            try:
                question = await ListeningCompletionModel.get(PydanticObjectId(question_id))
            except Exception:
                pass
            if not question:
                try:
                    question = await ListeningCompletionModel.get(question_id)
                except Exception:
                    pass

        if not question:
            raise ValueError("Question not found")

        segment = None
        if question.audio_segment_id:
            segment = await question.audio_segment_id.fetch()

        passage = await question.passage_id.fetch()
        
        if not segment:
            return {
                "questionId": question_id,
                "audioUrl": passage.audio_url,
                "startTime": 0,
                "endTime": 0,
                "transcript": "No transcript available for this question."
            }

        audio_url = segment.audio_file_url or passage.audio_url
        return {
            "questionId": question_id,
            "audioUrl": audio_url,
            "startTime": segment.start_time_ms,
            "endTime": segment.end_time_ms,
            "transcript": segment.transcript
        }
