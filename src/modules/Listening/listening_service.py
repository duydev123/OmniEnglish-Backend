from datetime import datetime
from typing import Dict, List

from .listening_util import ListeningUtil
from models.Listening import (
    ListeningPassageModel,
    UserListeningSessionModel,
    UserDictationSessionModel
)
from .listening_dto import (
    # Passages & History
    ListeningPassageSummaryResponse,
    ListeningHistoryItemResponse,
    
    # Comprehension
    ComprehensionSessionStartResponse,
    ListeningDraftRequest,
    ListeningDraftResponse,
    ListeningSubmitResponse,
    
    # Dictation
    DictationSessionStartResponse
)

class ListeningService:

    # ==========================================
    # 1. NHÓM QUẢN LÝ BÀI HỌC (PASSAGES) & LỊCH SỬ
    # ==========================================
    @staticmethod
    async def get_all_passages(page: int, limit: int) -> List[ListeningPassageSummaryResponse]:
        """Lấy danh sách các bài Listening có phân trang"""
        skip = (page - 1) * limit
        passages = await ListeningPassageModel.find_all().skip(skip).limit(limit).to_list()
        
        result = []
        for p in passages:
            result.append(ListeningPassageSummaryResponse(
                id=str(p.id),
                title=p.title,
                unit_code=p.unit_code,
                time_limit_minutes=p.time_limit_minutes,
                total_questions=p.total_questions
            ))
        return result

    @staticmethod
    async def get_passage_detail(passage_id: str, user_id: str) -> Dict:
        """Lấy chi tiết 1 passage và lịch sử làm bài tốt nhất của user (nếu có)"""
        passage = await ListeningUtil.get_passage(passage_id)
        
        # Có thể thêm logic query điểm cao nhất của user ở đây
        # Tạm thời trả về thông tin chi tiết của Passage
        return {
            "id": str(passage.id),
            "title": passage.title,
            "unit_code": passage.unit_code,
            "audio_url": passage.audio_url,
            "time_limit_minutes": passage.time_limit_minutes,
            "total_questions": passage.total_questions,
            "total_transcript_sentences": len(passage.interactive_transcript)
        }

    @staticmethod
    async def get_user_history(user_id: str, page: int, limit: int) -> List[ListeningHistoryItemResponse]:
        """Lấy lịch sử các bài đã làm (Cả Comprehension và Dictation), có phân trang"""
        # Lấy lịch sử Comprehension
        comp_sessions = await UserListeningSessionModel.find(
            UserListeningSessionModel.user_id == user_id,
            # UserListeningSessionModel.status == "COMPLETED"
        ).to_list()
        
        # Lấy lịch sử Dictation
        dict_sessions = await UserDictationSessionModel.find(
            UserDictationSessionModel.user_id == user_id,
            # UserDictationSessionModel.status == "COMPLETED"
        ).to_list()
        
        history = []
        
        for session in comp_sessions:
            passage = await session.passage_id.fetch()
            accuracy = session.result.accuracy_rate if session.result else 0.0
            history.append(ListeningHistoryItemResponse(
                session_id=str(session.id),
                passage_id=str(passage.id),
                passage_title=passage.title,
                session_type=session.session_type,
                status=session.status,
                accuracy_rate=accuracy,
                submitted_at=session.submitted_at
            ))
            
        for session in dict_sessions:
            passage = await session.passage_id.fetch()
            history.append(ListeningHistoryItemResponse(
                session_id=str(session.id),
                passage_id=str(passage.id),
                passage_title=passage.title,
                session_type="DICTATION",
                status=session.status,
                accuracy_rate=session.total_accuracy_rate,
                submitted_at=session.submitted_at
            ))
            
        # Sắp xếp mới nhất lên đầu
        history.sort(key=lambda x: x.submitted_at if x.submitted_at else datetime.min, reverse=True)
        
        # Cắt mảng theo page & limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        return history[start_idx:end_idx]


    # ==========================================
    # 2. XỬ LÝ COMPREHENSION (NGHE HIỂU)
    # ==========================================
    @staticmethod
    async def start_comprehension_session(user_id: str, passage_id: str) -> ComprehensionSessionStartResponse:
        passage = await ListeningUtil.get_passage(passage_id)
        session = await ListeningUtil.get_or_create_comprehension_session(user_id, passage_id)
        
        multiple_choices = await ListeningUtil.format_multiple_choices(passage_id)
        completions = await ListeningUtil.format_completions(passage_id)
        completed_questions = len(session.user_answers) if session.user_answers else 0
        
        return ComprehensionSessionStartResponse(
            session_id=str(session.id),
            passage_id=passage_id,
            session_type="COMPREHENSION",
            title=passage.title,
            unit_code=passage.unit_code,
            audio_url=passage.audio_url,
            time_limit_minutes=passage.time_limit_minutes,
            completed_questions=completed_questions,
            total_questions=passage.total_questions,
            multiple_choices=multiple_choices,
            completions=completions
        )

    @staticmethod
    async def get_comprehension_draft(session_id: str) -> Dict:
        return await ListeningUtil.get_comprehension_draft(session_id)

    @staticmethod
    async def save_comprehension_draft(session_id: str, payload: ListeningDraftRequest) -> ListeningDraftResponse:
        result = await ListeningUtil.save_comprehension_draft(
            session_id=session_id,
            user_answers=payload.user_answers,
            time_remaining_seconds=payload.time_remaining_seconds
        )
        return ListeningDraftResponse(
            session_id=session_id,
            status="IN_PROGRESS",
            message=result.get("message", "Draft saved successfully")
        )

    @staticmethod
    async def submit_comprehension_answers(session_id: str, payload: ListeningDraftRequest) -> ListeningSubmitResponse:
        return await ListeningUtil.grade_comprehension(
            session_id=session_id,
            user_answers=payload.user_answers
        )

    @staticmethod
    async def get_comprehension_session_result(session_id: str) -> Dict:
        session = await ListeningUtil._get_comprehension_session(session_id)
        if not session: raise ValueError("Comprehension Session not found")
        passage = await session.passage_id.fetch()
        result_data = session.result
        
        return {
            "success": True,
            "session_id": str(session.id),
            "user_id": session.user_id,
            "passage_id": str(passage.id),
            "passage_title": passage.title,
            "session_type": session.session_type,
            "status": session.status,
            "user_answers": [ans.dict() for ans in session.user_answers] if session.user_answers else [],
            "score": result_data.score if result_data else 0,
            "accuracy_rate": result_data.accuracy_rate if result_data else 0,
            "xp_earned": result_data.xp_earned if result_data else 0,
            "competency_matrix": result_data.competency_matrix if result_data else {},
            "detailed_question_review": [q.dict() for q in result_data.detailed_question_review] if result_data and hasattr(result_data, 'detailed_question_review') else [],
            "started_at": session.started_at,
            "submitted_at": session.submitted_at
        }


    # ==========================================
    # 3. XỬ LÝ DICTATION (CHÉP CHÍNH TẢ)
    # ==========================================
    @staticmethod
    async def start_dictation_session(user_id: str, passage_id: str) -> DictationSessionStartResponse:
        passage = await ListeningUtil.get_passage(passage_id)
        session = await ListeningUtil.get_or_create_dictation_session(user_id, passage_id)
        
        transcript = await ListeningUtil.format_transcript(passage)
        vocabulary = await ListeningUtil.format_vocabulary(passage)
        
        return DictationSessionStartResponse(
            session_id=str(session.id),
            passage_id=passage_id,
            session_type="DICTATION",
            title=passage.title,
            audio_url=passage.audio_url,
            time_limit_minutes=passage.time_limit_minutes,
            interactive_transcript=transcript,
            key_vocabulary=vocabulary,
            total_questions=len(transcript) # Số câu dictation bằng số câu transcript
        )

    @staticmethod
    async def get_dictation_draft(session_id: str) -> Dict:
        return await ListeningUtil.get_dictation_draft(session_id)

    @staticmethod
    async def grade_and_save_dictation_sentence(session_id: str, transcript_index: int, user_typed_text: str) -> Dict:
        return await ListeningUtil.grade_and_save_dictation_sentence(
            session_id=session_id,
            transcript_index=transcript_index,
            user_typed_text=user_typed_text
        )

    @staticmethod
    async def submit_dictation_session(session_id: str) -> Dict:
        return await ListeningUtil.submit_dictation_session(session_id)

    @staticmethod
    async def get_dictation_session_result(session_id: str) -> Dict:
        session = await ListeningUtil._get_dictation_session(session_id)
        if not session: raise ValueError("Dictation Session not found")
        passage = await session.passage_id.fetch()
        
        return {
            "success": True,
            "session_id": str(session.id),
            "user_id": session.user_id,
            "passage_id": str(passage.id),
            "passage_title": passage.title,
            "session_type": "DICTATION",
            "status": session.status,
            "total_accuracy_rate": session.total_accuracy_rate,
            "total_words_typed": session.total_words_typed,
            "sentence_histories": session.sentence_histories,
            "started_at": session.started_at,
            "submitted_at": session.submitted_at
        }
        