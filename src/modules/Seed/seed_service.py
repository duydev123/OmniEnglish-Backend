from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingFillBlankModel,
    ReadingHeadingMatchingModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)

from .reading_mock import MOCK_READING_PASSAGES

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