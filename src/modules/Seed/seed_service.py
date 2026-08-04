from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingFillBlankModel,
    ReadingHeadingMatchingModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)
from models.Listening import (
    ListeningPassageModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)
from .reading_mock import MOCK_READING_PASSAGES
from .listening_mock import MOCK_LISTENING_PASSAGES


class SeedService:
    
    # ==========================================
    # SEED READING
    # ==========================================
    async def seed_reading_only(self) -> dict:
        """Seed dữ liệu Reading"""
        # 1. Xóa sạch dữ liệu cũ
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
            "message": f"🌱 Successfully seeded {inserted_count} Reading Passages!",
            "stats": stats
        }

    # ==========================================
    # SEED LISTENING (THÊM MỚI)
    # ==========================================
    async def seed_listening_only(self) -> dict:
        """Seed dữ liệu Listening"""
        # 1. Xóa sạch dữ liệu cũ
        await ListeningPassageModel.delete_all()
        await ListeningMultipleChoiceModel.delete_all()
        await ListeningCompletionModel.delete_all()
        await UserListeningSessionModel.delete_all()

        inserted_count = 0
        stats = {
            "passages": 0,
            "multiple_choices": 0,
            "completions": 0
        }
        
        # 2. Loop qua danh sách Passage mock và lưu vào DB
        for item in MOCK_LISTENING_PASSAGES:
            passage = ListeningPassageModel(**item["passage"])
            await passage.insert()
            inserted_count += 1
            stats["passages"] += 1

            # Insert Multiple Choices
            for mc in item.get("multiple_choices", []):
                doc = ListeningMultipleChoiceModel(passage_id=passage, **mc)
                await doc.insert()
                stats["multiple_choices"] += 1

            # Insert Completions
            for comp in item.get("completions", []):
                doc = ListeningCompletionModel(passage_id=passage, **comp)
                await doc.insert()
                stats["completions"] += 1

        return {
            "status": "success",
            "message": f"🌱 Successfully seeded {inserted_count} Listening Passages!",
            "stats": stats
        }

    # ==========================================
    # SEED TẤT CẢ (READING + LISTENING)
    # ==========================================
    async def seed_all(self) -> dict:
        """Seed tất cả dữ liệu (Reading + Listening)"""
        reading_result = await self.seed_reading_only()
        listening_result = await self.seed_listening_only()
        
        return {
            "status": "success",
            "message": "🌱 Successfully seeded ALL data (Reading + Listening)!",
            "reading": reading_result,
            "listening": listening_result
        }