# src/modules/Speaking/speaking_service.py
from fastapi import HTTPException, status, UploadFile
from typing import Optional, List, Dict
from beanie.odm.operators.find.evaluation import RegEx
from beanie import PydanticObjectId
from .speaking_util import SpeakingUtil
from models.Speaking import (
    SpeakingTopicModel,
    SpeakingPromptModel,
    UserSpeakingTestSessionModel,
    QuestionDetailItem
)
from .speaking_dto import (
    SpeakingTopicSummaryResponse,
    SpeakingPromptResponse,
    SpeakingSessionStartResponse,
    SpeakingSegmentSubmitResponse,
    SpeakingSubmitResponse
)
class SpeakingService:
    # ==========================================
    # 1. QUẢN LÝ DANH SÁCH ĐỀ THI / TOPICS
    # ==========================================
    @staticmethod
    async def get_all_topics(page: int, limit: int, is_full_test: Optional[bool]) -> List[SpeakingTopicSummaryResponse]:
        """Lấy danh sách topic có phân trang và filter."""
        skip = (page - 1) * limit
        
        # Xây dựng Query
        query = {}
        if is_full_test is not None:
            query["is_full_test"] = is_full_test

        # Fetch topics từ Database
        topics = await SpeakingTopicModel.find(query).skip(skip).limit(limit).to_list()
        
        # Lấy count số lượng prompts cho từng topic
        result = []
        for topic in topics:
            prompt_count = await SpeakingPromptModel.find(
                SpeakingPromptModel.topic_id.id == topic.id
            ).count()
            
            result.append(SpeakingTopicSummaryResponse(
                id=str(topic.id),
                title=topic.title,
                description=topic.description,
                tags=topic.tags,
                is_full_test=topic.is_full_test,
                prompt_count=prompt_count
            ))
            
        return result

    @staticmethod
    async def get_prompts_by_topic(topic_id: str) -> Dict[str, List[SpeakingPromptResponse]]:
        """Lấy tất cả prompts của một topic và nhóm theo Part."""
        # Check topic tồn tại
        topic = await SpeakingTopicModel.get(topic_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy bộ đề Speaking này!"
            )

        # Lấy tất cả câu hỏi thuộc Topic
        prompts = await SpeakingPromptModel.find(
            SpeakingPromptModel.topic_id.id == topic.id
        ).to_list()

        # Format sang DTO
        formatted_prompts = [
            SpeakingPromptResponse(
                id=str(p.id),
                topic_id=str(p.topic_id.ref.id),
                part=p.part,
                sub_topic=p.sub_topic,
                question_text=p.question_text,
                examiner_audio_url=p.examiner_audio_url,
                useful_vocabulary=p.useful_vocabulary,
                ielts_tips=p.ielts_tips,
                examiner_tip=p.examiner_tip,
                response_structure=p.response_structure
            ) for p in prompts
        ]

        # Nhóm theo Part để Frontend dễ render UI (Part 1, Part 2, Part 3)
        grouped_prompts = {
            "PART_1": [p for p in formatted_prompts if p.part == "PART_1"],
            "PART_2": [p for p in formatted_prompts if p.part == "PART_2"],
            "PART_3": [p for p in formatted_prompts if p.part == "PART_3"],
            "SHADOWING": [p for p in formatted_prompts if p.part == "SHADOWING"]
        }

        # Loại bỏ các Part không có câu hỏi nào cho payload gọn gàng
        return {k: v for k, v in grouped_prompts.items() if len(v) > 0}

    @staticmethod
    async def start_session_by_topic(user_id: str, topic_id: str, test_type: str) -> SpeakingSessionStartResponse:
        """Tạo Session thi/luyện tập theo bộ đề (Topic)."""
        if not PydanticObjectId.is_valid(topic_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ID bộ đề không hợp lệ!"
            )

        # 1. Kiểm tra Topic có tồn tại không
        topic = await SpeakingTopicModel.get(PydanticObjectId(topic_id))
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy bộ đề này!"
            )

        # 2. Lấy danh sách prompts thuộc topic để tìm câu hỏi đầu tiên
        prompts = await SpeakingPromptModel.find(
            SpeakingPromptModel.topic_id.id == topic.id
        ).to_list()

        if not prompts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bộ đề này hiện chưa có câu hỏi nào!"
            )

        # Nếu chọn theo Part cụ thể (PART_1, PART_2, PART_3), lọc lấy câu hỏi tương ứng
        if test_type in ["PART_1", "PART_2", "PART_3", "SHADOWING"]:
            filtered_prompts = [p for p in prompts if p.part == test_type]
            if filtered_prompts:
                prompts = filtered_prompts

        # Sắp xếp nhẹ hoặc chọn câu hỏi đầu tiên
        first_prompt = prompts[0]

        # 3. Tạo mới Session trong MongoDB với status IN_PROGRESS
        session = UserSpeakingTestSessionModel(
            user_id=user_id,
            topic_id=topic,
            test_type=test_type,
            title=topic.title,
            status="IN_PROGRESS"
        )
        await session.insert()

        # 4. Format câu hỏi đầu tiên sang DTO
        target_topic_id = str(first_prompt.topic_id.ref.id) if hasattr(first_prompt.topic_id, "ref") else str(first_prompt.topic_id.id)
        current_prompt_dto = SpeakingPromptResponse(
            id=str(first_prompt.id),
            topic_id=target_topic_id,
            part=first_prompt.part,
            sub_topic=first_prompt.sub_topic,
            question_text=first_prompt.question_text,
            examiner_audio_url=first_prompt.examiner_audio_url,
            useful_vocabulary=first_prompt.useful_vocabulary or [],
            ielts_tips=first_prompt.ielts_tips or [],
            examiner_tip=first_prompt.examiner_tip,
            response_structure=first_prompt.response_structure or []
        )

        return SpeakingSessionStartResponse(
            session_id=str(session.id),
            topic_id=str(topic.id),
            prompt_id=str(first_prompt.id),
            test_type=test_type,
            status="IN_PROGRESS",
            current_prompt=current_prompt_dto
        )

    @staticmethod
    async def start_session_by_prompt(user_id: str, prompt_id: str) -> SpeakingSessionStartResponse:
        """Tạo Session khi luyện tập ngẫu nhiên 1 câu hỏi lẻ (Prompt)."""
        if not PydanticObjectId.is_valid(prompt_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ID câu hỏi không hợp lệ!"
            )

        # 1. Kiểm tra Prompt có tồn tại không
        prompt = await SpeakingPromptModel.get(PydanticObjectId(prompt_id))
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy câu hỏi này!"
            )

        # 2. Tạo mới Session trong MongoDB
        session = UserSpeakingTestSessionModel(
            user_id=user_id,
            prompt_id=prompt,
            test_type=prompt.part, # Lấy ngầm test_type theo part của prompt (VD: PART_1, SHADOWING)
            title=f"Practice: {prompt.question_text[:30]}...",
            status="IN_PROGRESS"
        )
        await session.insert()

        # 3. Format Prompt sang DTO
        target_topic_id = str(prompt.topic_id.ref.id) if hasattr(prompt.topic_id, "ref") else str(prompt.topic_id.id)
        current_prompt_dto = SpeakingPromptResponse(
            id=str(prompt.id),
            topic_id=target_topic_id,
            part=prompt.part,
            sub_topic=prompt.sub_topic,
            question_text=prompt.question_text,
            examiner_audio_url=prompt.examiner_audio_url,
            useful_vocabulary=prompt.useful_vocabulary or [],
            ielts_tips=prompt.ielts_tips or [],
            examiner_tip=prompt.examiner_tip,
            response_structure=prompt.response_structure or []
        )

        return SpeakingSessionStartResponse(
            session_id=str(session.id),
            topic_id=target_topic_id,
            prompt_id=str(prompt.id),
            test_type=prompt.part,
            status="IN_PROGRESS",
            current_prompt=current_prompt_dto
        )
    # ==========================================
    # 3. CHẤM ĐIỂM TỪNG CÂU (SEGMENT EVALUATION)
    # ==========================================
    @staticmethod
    async def process_and_save_segment(
        user_id: str,
        session_id: str,
        prompt_id: str,
        audio_file: UploadFile
    ) -> SpeakingSegmentSubmitResponse:
        """Xử lý upload audio, chấm điểm câu lẻ và cập nhật vào Session."""
        # 1. Validate ID
        if not PydanticObjectId.is_valid(session_id) or not PydanticObjectId.is_valid(prompt_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID hoặc Prompt ID không hợp lệ!"
            )

        # 2. Lấy Session
        session = await UserSpeakingTestSessionModel.get(PydanticObjectId(session_id))
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên luyện tập này!"
            )

        if session.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bài thi này đã hoàn thành!"
            )

        # 3. Lấy Prompt câu hỏi
        prompt = await SpeakingPromptModel.get(PydanticObjectId(prompt_id))
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy câu hỏi này!"
            )

        # 4. Upload Audio & Gọi AI Chấm điểm câu này
        await SpeakingUtil.validate_audio_file(audio_file)
        audio_url = await SpeakingUtil.upload_audio_to_cloud(audio_file, folder=f"speaking/{session_id}")
        eval_res = await SpeakingUtil.evaluate_single_audio_segment(audio_url, prompt.question_text)

        transcript = eval_res.get("transcript", "")
        segment_score = eval_res.get("segment_score", 0.0)
        pron_score = eval_res.get("pronunciation_score", 0.0)
        fluency_score = eval_res.get("fluency_score", 0.0)
        lexical_score = eval_res.get("lexical_score", 0.0)
        grammar_score = eval_res.get("grammar_score", 0.0)
        feedback = eval_res.get("feedback", "")
        words_detail = eval_res.get("words_detail", []) # Lấy dữ liệu âm tiết

        question_found = False
        for item in session.questions_detail:
            if getattr(item, "prompt_id", None) == prompt_id or item.question_text == prompt.question_text:
                item.prompt_id = prompt_id
                item.user_audio_url = audio_url
                item.user_transcript = transcript
                item.segment_score = segment_score
                item.pronunciation_score = pron_score
                item.fluency_score = fluency_score
                item.lexical_score = lexical_score
                item.grammar_score = grammar_score
                item.ai_feedback = feedback
                item.words_detail = words_detail # Lưu vào mảng
                item.is_graded = True
                question_found = True
                break

        if not question_found:
            session.questions_detail.append(
                QuestionDetailItem(
                    prompt_id=prompt_id,
                    question_text=prompt.question_text,
                    user_transcript=transcript,
                    user_audio_url=audio_url,
                    segment_score=segment_score,
                    pronunciation_score=pron_score,
                    fluency_score=fluency_score,
                    lexical_score=lexical_score,
                    grammar_score=grammar_score,
                    ai_feedback=feedback,
                    words_detail=words_detail, # Lưu vào mảng
                    is_graded=True
                )
            )

        if session.prompt_id and not session.topic_id:
            session.pronunciation_score = pron_score
            session.fluency_score = fluency_score
            session.lexical_score = lexical_score
            session.grammar_score = grammar_score
            session.overall_band_score = segment_score
            session.status = "COMPLETED"

        await session.save()

        # Trả về Response chứa đầy đủ audio_url và mảng âm tiết
        return SpeakingSegmentSubmitResponse(
            session_id=str(session.id),
            prompt_id=prompt_id,
            status=session.status,
            user_transcript=transcript,
            user_audio_url=audio_url, # Trả về URL để FE play
            segment_score=segment_score,
            pronunciation_score=pron_score,
            fluency_score=fluency_score,
            lexical_score=lexical_score,
            grammar_score=grammar_score,
            realtime_feedback=feedback,
            words_detail=words_detail # Trả về mảng bóc tách âm tiết
        )
    # ==========================================
    # 4. TỔNG KẾT BÀI THI (SUBMIT & COMPLETE)
    # ==========================================
    @staticmethod
    async def evaluate_session(user_id: str, session_id: str) -> SpeakingSubmitResponse:
        """Tổng kết toàn bộ điểm các câu trong Session và đổi status thành COMPLETED."""
        if not PydanticObjectId.is_valid(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID không hợp lệ!"
            )

        session = await UserSpeakingTestSessionModel.get(PydanticObjectId(session_id))
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên làm bài!"
            )

        if not session.questions_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn chưa thực hiện ghi âm câu hỏi nào trong bài thi này!"
            )

        # 1. Tính trung bình Pronunciation và Fluency từ các câu đã chấm
        graded_questions = [q for q in session.questions_detail if getattr(q, 'is_graded', False)]
        total_q = len(graded_questions)
        
        if total_q == 0:
            raise HTTPException(status_code=400, detail="Chưa có câu hỏi nào được chấm điểm!")

        # Chỉ việc TÍNH TRUNG BÌNH CỘNG TỪ CÁC CÂU LẺ
        avg_pron = sum(q.pronunciation_score or 0.0 for q in graded_questions) / total_q
        avg_fluency = sum(q.fluency_score or 0.0 for q in graded_questions) / total_q
        avg_lexical = sum(q.lexical_score or 0.0 for q in graded_questions) / total_q
        avg_grammar = sum(q.grammar_score or 0.0 for q in graded_questions) / total_q
        avg_overall = sum(q.overall_score or 0.0 for q in graded_questions) / total_q

        # Lưu vào Session
        session.pronunciation_score = round(avg_pron, 1)
        session.fluency_score = round(avg_fluency, 1)
        session.lexical_score = round(avg_lexical, 1)
        session.grammar_score = round(avg_grammar, 1)
        session.overall_band_score = round(avg_overall, 1)
        
        session.status = "COMPLETED"
        await session.save()

        return SpeakingSubmitResponse(
            session_id=str(session.id),
            status="COMPLETED",
            message="Bài thi Speaking đã được hoàn thành!"
        )