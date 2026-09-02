# modules/Listening/listening_util.py
import random
from datetime import datetime, UTC
from typing import Dict, List, Optional
from beanie import PydanticObjectId

# Đảm bảo ông đã khai báo UserDictationSessionModel và DictationSentenceHistory trong models/Listening.py
from models.Listening import (
    ListeningPassageModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel,
    UserDictationSessionModel,   # Model mới cho Dictation
    DictationSentenceHistory,    # Model lịch sử câu Dictation
    UserAnswer,
    ListeningResult
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

class ListeningUtil:

    # ==========================================
    # 1. CÁC HÀM TIỆN ÍCH DÙNG CHUNG (PASSAGE)
    # ==========================================
    @staticmethod
    async def get_passage(passage_id: str) -> ListeningPassageModel:
        """Lấy passage theo ID"""
        passage = await ListeningPassageModel.get(passage_id)
        if not passage:
            raise ValueError("Passage not found")
        return passage

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

    # ==========================================
    # 2. XỬ LÝ COMPREHENSION (NGHE HIỂU)
    # ==========================================
    @staticmethod
    async def _get_comprehension_session(session_id: str) -> Optional[UserListeningSessionModel]:
        if not session_id: return None
        try:
            session = await UserListeningSessionModel.get(PydanticObjectId(session_id))
            if session: return session
        except Exception:
            pass
        return await UserListeningSessionModel.get(session_id)

    @staticmethod
    async def get_or_create_comprehension_session(user_id: str, passage_id: str) -> UserListeningSessionModel:
        passage = await ListeningUtil.get_passage(passage_id)
        existing_session = await UserListeningSessionModel.find_one(
            UserListeningSessionModel.user_id == user_id,
            UserListeningSessionModel.passage_id.id == PydanticObjectId(passage_id),
            UserListeningSessionModel.session_type == "COMPREHENSION",
            UserListeningSessionModel.status == "IN_PROGRESS"
        )
        if existing_session:
            return existing_session
            
        session = UserListeningSessionModel(
            user_id=user_id,
            passage_id=passage,
            session_type="COMPREHENSION",
            time_remaining_seconds=passage.time_limit_minutes * 60,
            status="IN_PROGRESS"
        )
        await session.save()
        return session

    @staticmethod
    async def format_multiple_choices(passage_id: str) -> List[ListeningMultipleChoiceResponse]:
        multiple_choices = await ListeningMultipleChoiceModel.find(
            ListeningMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        for mc in multiple_choices:
            random.shuffle(mc.options)
        return [
            ListeningMultipleChoiceResponse(
                id=str(m.id), order=m.order, question_text=m.question_text, options=m.options
            ) for m in multiple_choices
        ]

    @staticmethod
    async def format_completions(passage_id: str) -> List[ListeningCompletionResponse]:
        completions = await ListeningCompletionModel.find(
            ListeningCompletionModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        return [
            ListeningCompletionResponse(
                id=str(c.id), order=c.order, template_text=c.template_text, case_sensitive=c.case_sensitive
            ) for c in completions
        ]

    @staticmethod
    async def get_comprehension_draft(session_id: str) -> Dict:
        session = await ListeningUtil._get_comprehension_session(session_id)
        if not session: raise ValueError("Session not found")
        passage = await session.passage_id.fetch()
        
        return {
            "success": True,
            "session_id": str(session.id),
            "user_id": session.user_id,
            "passage_id": str(passage.id),
            "status": session.status,
            "user_answers": [ans.dict() for ans in session.user_answers] if session.user_answers else [],
            "time_remaining_seconds": session.time_remaining_seconds or 0,
            "completed_questions": sum(1 for a in session.user_answers if getattr(a, "answer", None) and str(a.answer).strip() != "") if session.user_answers else 0,
            "total_questions": passage.total_questions
        }

    @staticmethod
    async def save_comprehension_draft(session_id: str, user_answers: List[UserAnswer], time_remaining_seconds: int) -> Dict:
        session = await ListeningUtil._get_comprehension_session(session_id)
        if not session: raise ValueError("Session not found")
        passage = await session.passage_id.fetch()
        
        session.user_answers = user_answers
        session.time_remaining_seconds = time_remaining_seconds
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        return {
            "success": True,
            "message": "Comprehension draft saved successfully",
            "session_id": session_id,
            "completed_questions": min(sum(1 for a in user_answers if getattr(a, "answer", None) and str(a.answer).strip() != ""), passage.total_questions)
        }

    @staticmethod
    async def grade_comprehension(session_id: str, user_answers: List[UserAnswer]) -> ListeningSubmitResponse:
        session = await ListeningUtil._get_comprehension_session(session_id)
        if not session: raise ValueError("Session not found")
        
        passage = await session.passage_id.fetch()
        passage_id = passage.id
        
        multiple_choices = await ListeningMultipleChoiceModel.find(
            ListeningMultipleChoiceModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        completions = await ListeningCompletionModel.find(
            ListeningCompletionModel.passage_id.id == PydanticObjectId(passage_id)
        ).to_list()
        
        detailed_review = []
        competency_matrix = {
            "Global Understanding": 0,
            "Specific Information Retrieval": 0,
            "Inference & Tone": 0,
            "Vocabulary": 0
        }
        competency_counts = {k: 0 for k in competency_matrix.keys()}
        
        correct_count = 0
        total_questions = len(multiple_choices) + sum(len(c.correct_answers) for c in completions)
        
        user_answers_dict = {str(ans.question_id): ans.answer for ans in user_answers}
        graded_user_answers = []
        
        # 1. Chấm Multiple Choice
        for mc in multiple_choices:
            question_id = str(mc.id)
            user_answer_val = user_answers_dict.get(question_id, "")
            is_correct = user_answer_val == mc.correct_answer
            
            if is_correct: correct_count += 1
            
            comp_type = mc.competency_type or "Global Understanding"
            if comp_type in competency_counts:
                competency_counts[comp_type] += 1
                if is_correct: competency_matrix[comp_type] += 1
                
            graded_user_answers.append(UserAnswer(
                question_id=PydanticObjectId(question_id),
                question_type="MULTIPLE_CHOICE",
                answer=user_answer_val,
                is_correct=is_correct
            ))
            
            detailed_review.append(QuestionReviewDetail(
                question_text=mc.question_text,
                your_answer=user_answer_val or "Not answered",
                correct_answer=mc.correct_answer,
                is_correct=is_correct,
                timestamp_clip=mc.timestamp_clip,
                learning_hint=mc.learning_hint or ListeningUtil._get_default_hint(is_correct)
            ))

        # 2. Chấm Completion
        for comp in completions:
            question_id = str(comp.id)
            user_answer_val = user_answers_dict.get(question_id, {})
            if not isinstance(user_answer_val, dict): user_answer_val = {}
            
            is_comp_fully_correct = True
            for gap_id, correct_answer in comp.correct_answers.items():
                user_gap_answer = user_answer_val.get(gap_id, "")
                if comp.case_sensitive:
                    is_correct = user_gap_answer == correct_answer
                else:
                    is_correct = user_gap_answer.lower().strip() == correct_answer.lower().strip()
                    
                if is_correct: correct_count += 1
                else: is_comp_fully_correct = False
                
                comp_type = "Specific Information Retrieval"
                if comp_type in competency_counts:
                    competency_counts[comp_type] += 1
                    if is_correct: competency_matrix[comp_type] += 1
                    
                detailed_review.append(QuestionReviewDetail(
                    question_text=f"Fill in the blank: {comp.template_text.replace(f'[{gap_id}]', '_____')}",
                    your_answer=user_gap_answer or "Not answered",
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                    timestamp_clip=None,
                    learning_hint="Review the audio segment to find the missing word."
                ))
                
            graded_user_answers.append(UserAnswer(
                question_id=PydanticObjectId(question_id),
                question_type="COMPLETION",
                answer=user_answer_val,
                is_correct=is_comp_fully_correct
            ))

        for comp_type in competency_matrix:
            if competency_counts[comp_type] > 0:
                competency_matrix[comp_type] = round((competency_matrix[comp_type] / competency_counts[comp_type]) * 100, 2)
                
        accuracy_rate = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        xp_earned = ListeningUtil._calculate_xp(accuracy_rate, total_questions)
        score_summary = f"{correct_count} out of {total_questions} Correct"
        
        session.user_answers = graded_user_answers
        session.time_remaining_seconds = 0
        session.status = "COMPLETED"
        session.submitted_at = datetime.now(UTC)
        session.updated_at = datetime.now(UTC)
        
        session.result = ListeningResult(
            score=correct_count,
            accuracy_rate=round(accuracy_rate, 2),
            xp_earned=xp_earned,
            competency_matrix=competency_matrix,
            detailed_question_review=[d.dict() for d in detailed_review]
        )
        await session.save()
        
        return ListeningSubmitResponse(
            session_id=session_id,
            session_type="COMPREHENSION",
            status="COMPLETED",
            accuracy_rate=round(accuracy_rate, 2),
            score_summary=score_summary,
            xp_earned=xp_earned,
            competency_matrix=competency_matrix,
            detailed_question_review=detailed_review
        )

    # ==========================================
    # 3. XỬ LÝ DICTATION (CHÉP CHÍNH TẢ)
    # ==========================================
    @staticmethod
    async def _get_dictation_session(session_id: str) -> Optional[UserDictationSessionModel]:
        if not session_id: return None
        try:
            session = await UserDictationSessionModel.get(PydanticObjectId(session_id))
            if session: return session
        except Exception:
            pass
        return await UserDictationSessionModel.get(session_id)

    @staticmethod
    async def get_or_create_dictation_session(user_id: str, passage_id: str) -> UserDictationSessionModel:
        passage = await ListeningUtil.get_passage(passage_id)
        existing_session = await UserDictationSessionModel.find_one(
            UserDictationSessionModel.user_id == user_id,
            UserDictationSessionModel.passage_id.id == PydanticObjectId(passage_id),
            UserDictationSessionModel.status == "IN_PROGRESS"
        )
        if existing_session:
            return existing_session
            
        session = UserDictationSessionModel(
            user_id=user_id,
            passage_id=passage,
            status="IN_PROGRESS"
        )
        await session.save()
        return session

    @staticmethod
    async def get_dictation_draft(session_id: str) -> Dict:
        """Lấy lại tiến độ gõ Dictation đang làm dở"""
        session = await ListeningUtil._get_dictation_session(session_id)
        if not session: raise ValueError("Dictation session not found")
        passage = await session.passage_id.fetch()
        
        return {
            "success": True,
            "session_id": str(session.id),
            "status": session.status,
            "total_questions": len(passage.interactive_transcript),
            "sentence_histories": session.sentence_histories # Trả về các câu đã check
        }

    @staticmethod
    async def grade_and_save_dictation_sentence(session_id: str, transcript_index: int, user_typed_text: str) -> Dict:
        """Chấm điểm và lưu lịch sử từng câu"""
        session = await ListeningUtil._get_dictation_session(session_id)
        if not session: raise ValueError("Dictation Session not found")
        if session.status == "COMPLETED":
            raise ValueError("Session is already completed. Cannot modify answers.")
            
        passage = await session.passage_id.fetch()
        if transcript_index < 0 or transcript_index >= len(passage.interactive_transcript):
            raise ValueError("Transcript index out of range")
            
        target_sentence = passage.interactive_transcript[transcript_index]
        original_sentence = target_sentence.get("en", "")
        original_words = original_sentence.split()
        user_words = user_typed_text.split() if user_typed_text else []
        
        transcript_comparison = []
        correct_words = 0
        missed_contractions = 0
        contractions = ["don't", "doesn't", "didn't", "can't", "won't", "shouldn't",
                        "wouldn't", "couldn't", "haven't", "hasn't", "hadn't", "isn't",
                        "aren't", "weren't", "wasn't", "i'm", "you're", "he's", "she's",
                        "it's", "we're", "they're", "i've", "you've", "we've", "they've"]
                        
        for i, original_word in enumerate(original_words):
            user_word = user_words[i] if i < len(user_words) else None
            is_correct = (user_word == original_word) if user_word else False
            if is_correct: correct_words += 1
            if original_word.lower() in contractions and not user_word: missed_contractions += 1
                
            transcript_comparison.append({
                "word": original_word,
                "user_word": user_word,
                "is_correct": is_correct
            })
            
        accuracy_rate = (correct_words / len(original_words)) * 100 if original_words else 0
        is_fully_correct = correct_words == len(original_words) and len(user_words) == len(original_words)
        
        history_record = DictationSentenceHistory(
            transcript_index=transcript_index,
            user_typed_text=user_typed_text,
            is_correct=is_fully_correct,
            accuracy_rate=round(accuracy_rate, 2),
            correct_words=correct_words,
            missed_contractions=missed_contractions,
            transcript_comparison=transcript_comparison,
            updated_at=datetime.now(UTC)
        )
        
        session.sentence_histories[str(transcript_index)] = history_record
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        session.sentence_histories[str(transcript_index)] = history_record
        session.updated_at = datetime.now(UTC)
        await session.save()
        
        # SỬA ĐOẠN RETURN NÀY:
        response_data = history_record.dict()
        response_data["words_typed"] = len(user_words) # Thêm field frontend đang đòi
        return response_data

    @staticmethod
    async def submit_dictation_session(session_id: str) -> Dict:
        """Chốt sổ bài Dictation"""
        session = await ListeningUtil._get_dictation_session(session_id)
        if not session: raise ValueError("Dictation Session not found")
            
        if session.status == "COMPLETED":
            return {"message": "Already completed", "status": session.status}
            
        total_accuracy = sum(item.accuracy_rate for item in session.sentence_histories.values())
        total_sentences_done = len(session.sentence_histories)
        
        session.total_accuracy_rate = round(total_accuracy / total_sentences_done, 2) if total_sentences_done > 0 else 0
        session.total_words_typed = sum(len(item.user_typed_text.split()) for item in session.sentence_histories.values())
        
        session.status = "COMPLETED"
        session.submitted_at = datetime.now(UTC)
        await session.save()
        
        return {
            "session_id": str(session.id),
            "status": session.status,
            "total_accuracy_rate": session.total_accuracy_rate,
            "total_words_typed": session.total_words_typed
        }

    # ==========================================
    # 4. CÁC HÀM TÍNH TOÁN BỔ TRỢ
    # ==========================================
    @staticmethod
    def _get_default_hint(is_correct: bool) -> str:
        if is_correct:
            return "Well done! This answer is correct."
        return "Incorrect. Review the audio again and try to understand the context."

    @staticmethod
    def _calculate_xp(accuracy_rate: float, total_questions: int) -> int:
        base_xp = total_questions * 10
        bonus_xp = 0
        if accuracy_rate >= 90:
            bonus_xp = base_xp * 0.5 
        elif accuracy_rate >= 70:
            bonus_xp = base_xp * 0.2
        return int(base_xp + bonus_xp)

    @staticmethod
    def _get_spelling_tip(accuracy_rate: float, missed_contractions: int) -> str:
        tips = []
        if accuracy_rate < 60:
            tips.append("Try listening to the audio again and focus on each word.")
        if missed_contractions > 3:
            tips.append("Pay attention to contractions like 'don't', 'can't' - they're common in spoken English.")
        if 60 <= accuracy_rate < 80:
            tips.append("Practice with slower speed or use the interactive transcript to check difficult words.")
        if accuracy_rate >= 80:
            tips.append("Great work! Your spelling is strong. Try to improve your typing speed.")
        return " ".join(tips) if tips else "Keep practicing to improve your dictation skills!"

    @staticmethod
    def _get_listening_insight(accuracy_rate: float) -> str:
        if accuracy_rate >= 90:
            return "Excellent listening comprehension! You've mastered this audio."
        elif accuracy_rate >= 70:
            return "Good job! You understand most of the content. Try to identify specific details next time."
        elif accuracy_rate >= 50:
            return "Fair effort. Consider listening multiple times and using the transcript to check difficult sections."
        else:
            return "Keep practicing! Start with slower audio and gradually increase speed. Focus on key vocabulary first."