from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingFillBlankModel,
    ReadingHeadingMatchingModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)

from .reading_mock import MOCK_READING_PASSAGES


from models.Speaking import SpeakingTopicModel, SpeakingPromptModel, UserSpeakingTestSessionModel
from .speaking_mock import MOCK_SPEAKING_DATA


from models.Speaking import SpeakingTopicModel, SpeakingPromptModel, UserSpeakingTestSessionModel, ShadowingSentenceModel

# 2. Thêm import mock data ở đầu file
from .shadowing_mock import MOCK_SHADOWING_DATA
class SeedService:
    async def seed_reading_only(self) -> dict:
        # 1. Xóa sạch dữ liệu cũ liên quan đến Reading
        await ReadingPassageModel.delete_all()
        await ReadingTrueFalseNotGivenModel.delete_all()
        await ReadingHeadingMatchingModel.delete_all()
        await ReadingFillBlankModel.delete_all()
        await ReadingMultipleChoiceModel.delete_all()
        await UserReadingSessionModel.delete_all()

        inserted_count = 0
        stats = {
            "passages": 0,
            "multiple_choices": 0,
            "heading_matchings": 0,
            "fill_blanks": 0,
            "true_false_not_given": 0
        }
        # 2. Loop qua danh sách Passage mock và lưu vào DB
        for item in MOCK_READING_PASSAGES:
            passage = ReadingPassageModel(**item["passage"])
            await passage.insert()
            inserted_count += 1
            stats["passages"] += 1

            # Insert Multiple Choices
            for mc in item.get("multiple_choices", []):
                doc = ReadingMultipleChoiceModel(passage_id=passage, **mc)
                await doc.insert()
                stats["multiple_choices"] += 1

            # Insert Heading Matchings
            for heading in item.get("heading_matchings", []):
                doc = ReadingHeadingMatchingModel(passage_id=passage, **heading)
                await doc.insert()
                stats["heading_matchings"] += 1

            # Insert Fill Blanks
            for fill in item.get("fill_blanks", []):
                doc = ReadingFillBlankModel(passage_id=passage, **fill)
                await doc.insert()
                stats["fill_blanks"] += 1

            # Insert True/False/Not Given
            for tfng in item.get("true_false_not_given", []):
                doc = ReadingTrueFalseNotGivenModel(passage_id=passage, **tfng)
                await doc.insert()
                stats["true_false_not_given"] += 1

        return {
            "status": "success",
            "message": f"🌱 Successfully seeded {inserted_count} Reading Passages and their questions!"
        }


    async def seed_speaking_only(self) -> dict:
        # 1. Xóa dữ liệu Speaking cũ
        await SpeakingTopicModel.delete_all()
        await SpeakingPromptModel.delete_all()
        await UserSpeakingTestSessionModel.delete_all()

        inserted_count = {
            "topics": 0,
            "prompts": 0
        }

        # 2. Duyệt qua mảng mock data và lưu vào DB
        for item in MOCK_SPEAKING_DATA:
            # Tạo Topic
            topic_doc = SpeakingTopicModel(**item["topic"])
            await topic_doc.insert()
            inserted_count["topics"] += 1

            # Tạo Prompts (Liên kết với Topic vừa tạo)
            for prompt_data in item["prompts"]:
                prompt_doc = SpeakingPromptModel(
                    topic_id=topic_doc, # Truyền Object/Link vào đây
                    **prompt_data
                )
                await prompt_doc.insert()
                inserted_count["prompts"] += 1

        return {
            "status": "success",
            "message": f"Successfully seeded {inserted_count['topics']} Speaking Topics and {inserted_count['prompts']} Prompts!"
        }
        
    async def seed_shadowing_only(self) -> dict:
        # Xóa sạch data cũ để tránh trùng lặp khi seed nhiều lần
        await ShadowingSentenceModel.delete_all()
        
        inserted_count = 0
        
        # Lặp qua mảng mock data và đẩy vào Database
        for item in MOCK_SHADOWING_DATA:
            doc = ShadowingSentenceModel(**item)
            await doc.insert()
            inserted_count += 1
            
        return {
            "status": "success",
            "message": f"Successfully seeded {inserted_count} Shadowing Sentences!"
        }