# src/modules/Speaking/speaking_service.py
from fastapi import HTTPException, status
from typing import Optional, List, Dict
from beanie.odm.operators.find.evaluation import RegEx
from beanie import PydanticObjectId
from models.Speaking import SpeakingTopicModel, SpeakingPromptModel, UserSpeakingTestSessionModel
from .speaking_dto import SpeakingTopicSummaryResponse, SpeakingPromptResponse, SpeakingSessionStartResponse, SpeakingPromptResponse

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