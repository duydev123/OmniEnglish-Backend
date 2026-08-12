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
    QuestionDetailItem,
    
)
from .speaking_dto import (
    SpeakingTopicSummaryResponse,
    SpeakingPromptResponse,
    SpeakingSessionStartResponse,
    SpeakingSegmentSubmitResponse,
    SpeakingSessionDetailResponse,
    SpeakingHistoryItemResponse,
    QuestionDetailReview
)
from models.Speaking import ShadowingSentenceModel
from .speaking_dto import ShadowingSentenceResponse, ShadowingEvaluateResponse

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
    async def get_prompt_detail(prompt_id: str) -> SpeakingPromptResponse:
        """Lấy chi tiết 1 câu hỏi (Prompt) bằng ID"""
        from beanie import PydanticObjectId
        from fastapi import HTTPException
        
        # Kiểm tra tính hợp lệ của ID
        if not PydanticObjectId.is_valid(prompt_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="ID prompt không hợp lệ"
            )
            
        # Truy vấn prompt từ database
        prompt = await SpeakingPromptModel.get(PydanticObjectId(prompt_id))
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Không tìm thấy câu hỏi (prompt) này"
            )
            
        # Xử lý Link reference của Beanie để lấy topic_id
        target_topic_id = str(prompt.topic_id.ref.id) if hasattr(prompt.topic_id, "ref") else str(prompt.topic_id.id)
        
        # Trả về DTO
        return SpeakingPromptResponse(
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
        
        # ==========================================
        # LOGIC TÌM CÂU HỎI TIẾP THEO CHO NÚT "NEXT"
        # ==========================================
        next_prompt_id = None
        target_topic_id = None
        
        if hasattr(prompt, "topic_id") and prompt.topic_id:
            target_topic_id = prompt.topic_id.ref.id if hasattr(prompt.topic_id, "ref") else prompt.topic_id.id
            
        if target_topic_id:
            # Lấy tất cả câu hỏi thuộc Topic này
            all_prompts_in_topic = await SpeakingPromptModel.find(
                SpeakingPromptModel.topic_id.id == target_topic_id
            ).to_list()
            
            # Tìm vị trí câu hiện tại, suy ra câu kế tiếp
            for i, p in enumerate(all_prompts_in_topic):
                if str(p.id) == prompt_id:
                    if i + 1 < len(all_prompts_in_topic):
                        next_prompt_id = str(all_prompts_in_topic[i + 1].id)
                    break

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
            words_detail=words_detail, # Trả về mảng bóc tách âm tiết
            next_prompt_id=next_prompt_id
        )
    # lấy danh sách các bài đã làm 

    @staticmethod
    async def get_session_detail(user_id: str, session_id: str) -> SpeakingSessionDetailResponse:
        """Lấy toàn bộ kết quả của 1 bài thi để render màn hình Result Analysis"""
        if not PydanticObjectId.is_valid(session_id):
            raise HTTPException(status_code=400, detail="Session ID không hợp lệ!")
            
        session = await UserSpeakingTestSessionModel.get(PydanticObjectId(session_id))
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài thi!")
            
        # Tính toán thời lượng (nếu lưu ở dạng timestamp)
        # Giả lập: duration_str = "12:30"
            
        return SpeakingSessionDetailResponse(
            session_id=str(session.id),
            test_type=session.test_type,
            title=session.title,
            duration_str=session.duration_str or "00:00",
            status=session.status,
            full_session_audio_url=session.full_session_audio_url,
            overall_band_score=session.overall_band_score,
            band_score_delta=session.band_score_delta,
            percentile_rank=session.percentile_rank,
            pronunciation_score=session.pronunciation_score,
            fluency_score=session.fluency_score,
            lexical_score=session.lexical_score,
            grammar_score=session.grammar_score,
            key_strengths=session.key_strengths,
            areas_for_growth=session.areas_for_growth,
            
            # SỬA LẠI ĐOẠN NÀY:
            questions_detail=[
                QuestionDetailReview(
                    question_text=q.question_text,
                    user_transcript=q.user_transcript,
                    user_audio_url=q.user_audio_url
                ) for q in session.questions_detail
            ] if session.questions_detail else [],
            
            ai_insights_summary=session.ai_insights_summary,
            detailed_criteria_feedback=session.detailed_criteria_feedback,
            next_milestone=session.next_milestone,
            recommended_resources=session.recommended_resources,
            created_at=session.created_at
        )
        
    # src/modules/Speaking/speaking_service.py

    @staticmethod
    async def get_user_history(
        user_id: str, 
        page: int, 
        limit: int,
        topic_id: Optional[str] = None,
        prompt_id: Optional[str] = None,
        part: Optional[str] = None
    ) -> List[SpeakingHistoryItemResponse]:
        
        skip = (page - 1) * limit
        
        # Bắt buộc lọc theo user_id
        search_criteria = [UserSpeakingTestSessionModel.user_id == user_id]
        
        # Lọc theo Part (Map vào test_type)
        if part:
            search_criteria.append(UserSpeakingTestSessionModel.test_type == part)
            
        # Lọc theo Topic ID (Chỉ lấy các Session của những Prompt thuộc Topic này)
        if topic_id:
            if not PydanticObjectId.is_valid(topic_id):
                raise HTTPException(status_code=400, detail="Topic ID không hợp lệ!")
            
            topic_oid = PydanticObjectId(topic_id)
            
            # 1. Tìm tất cả các câu hỏi (prompts) thuộc Topic này
            prompts_in_topic = await SpeakingPromptModel.find(
                SpeakingPromptModel.topic_id.id == topic_oid
            ).to_list()
            prompt_ids = [p.id for p in prompts_in_topic]
            
            # 2. Nếu topic có câu hỏi, lọc các Session chứa prompt_id nằm trong mảng trên
            if prompt_ids:
                search_criteria.append({"prompt_id.$id": {"$in": prompt_ids}})
            else:
                # Topic rỗng -> Chắc chắn không có lịch sử làm bài -> Trả về rỗng luôn cho lẹ
                return []

        # Lọc theo đúng 1 Prompt ID cụ thể (nếu có)
        if prompt_id:
            if not PydanticObjectId.is_valid(prompt_id):
                raise HTTPException(status_code=400, detail="Prompt ID không hợp lệ!")
            search_criteria.append(UserSpeakingTestSessionModel.prompt_id.id == PydanticObjectId(prompt_id))

        # Thực thi Query
        sessions = await UserSpeakingTestSessionModel.find(
            *search_criteria
        ).sort("-created_at").skip(skip).limit(limit).to_list()
        
        return [
            SpeakingHistoryItemResponse(
                session_id=str(s.id),
                test_type=s.test_type,
                title=s.title,
                overall_band_score=s.overall_band_score,
                duration_str=s.duration_str or "00:00",
                status=s.status,
                created_at=s.created_at
            ) for s in sessions
        ]
    
    
    
    
    @staticmethod
    async def get_shadowing_sentences(page: int, limit: int) -> List[ShadowingSentenceResponse]:
        skip = (page - 1) * limit
        sentences = await ShadowingSentenceModel.find().skip(skip).limit(limit).to_list()
        
        return [
            ShadowingSentenceResponse(
                id=str(s.id),
                target_skill=s.target_skill,
                english_text=s.english_text,
                ipa_text=s.ipa_text,
                audio_url=s.audio_url
            ) for s in sentences
        ]
    
    @staticmethod
    async def get_shadowing_sentence_detail(sentence_id: str) -> ShadowingSentenceResponse:
        from beanie import PydanticObjectId
        from fastapi import HTTPException
        from models.Speaking import ShadowingSentenceModel
        from .speaking_dto import ShadowingSentenceResponse

        # Kiểm tra tính hợp lệ của ObjectId
        if not PydanticObjectId.is_valid(sentence_id):
            raise HTTPException(status_code=400, detail="ID câu không hợp lệ")
            
        # Truy vấn câu Shadowing từ Database
        sentence = await ShadowingSentenceModel.get(PydanticObjectId(sentence_id))
        
        if not sentence:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu Shadowing này")
            
        # Trả về kết quả theo chuẩn DTO
        return ShadowingSentenceResponse(
            id=str(sentence.id),
            target_skill=sentence.target_skill,
            english_text=sentence.english_text,
            ipa_text=sentence.ipa_text,
            audio_url=sentence.audio_url
        )

    @staticmethod
    async def evaluate_shadowing_segment(sentence_id: str, audio_file: UploadFile) -> ShadowingEvaluateResponse:
        from beanie import PydanticObjectId
        from fastapi import HTTPException
        from .speaking_util import SpeakingUtil
        from models.Speaking import ShadowingSentenceModel
        from .speaking_dto import ShadowingEvaluateResponse

        if not PydanticObjectId.is_valid(sentence_id):
            raise HTTPException(status_code=400, detail="ID câu không hợp lệ")
            
        sentence = await ShadowingSentenceModel.get(PydanticObjectId(sentence_id))
        if not sentence:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu Shadowing này")
            
        # 1. Kiểm tra định dạng file
        await SpeakingUtil.validate_audio_file(audio_file)
        
        # 2. BỎ ĐOẠN UPLOAD CLOUDINARY ĐI. 
        # Ném thẳng audio_file vào hàm evaluate_shadowing_audio luôn
        eval_res = await SpeakingUtil.evaluate_shadowing_audio(audio_file, sentence.english_text)
        
        return ShadowingEvaluateResponse(
            accuracy_score=eval_res["accuracy_score"],
            fluency_score=eval_res["fluency_score"],
            user_transcript=eval_res["transcript"],
            words_detail=eval_res["words_detail"]
        )