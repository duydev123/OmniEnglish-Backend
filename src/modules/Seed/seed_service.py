from models.Reading import (
    ReadingPassageModel,
    ReadingVocabMatchingModel,
    ReadingSentenceCompletionModel,
    ReadingMultipleChoiceModel,
    UserReadingSessionModel
)
from .reading_mock import MOCK_READING_PASSAGES

class SeedService:
    async def seed_reading_only(self) -> dict:
        # 1. Xóa sạch dữ liệu cũ liên quan đến Reading
        await ReadingPassageModel.delete_all()
        await ReadingVocabMatchingModel.delete_all()
        await ReadingSentenceCompletionModel.delete_all()
        await ReadingMultipleChoiceModel.delete_all()
        await UserReadingSessionModel.delete_all()

        inserted_count = 0

        # 2. Loop qua danh sách Passage mock và lưu vào DB
        for item in MOCK_READING_PASSAGES:
            passage = ReadingPassageModel(**item["passage"])
            await passage.insert()
            inserted_count += 1

            # Insert Vocab Matchings
            for vocab in item.get("vocab_matchings", []):
                doc = ReadingVocabMatchingModel(passage_id=passage, **vocab)
                await doc.insert()

            # Insert Sentence Completions
            for completion in item.get("sentence_completions", []):
                doc = ReadingSentenceCompletionModel(passage_id=passage, **completion)
                await doc.insert()

            # Insert Multiple Choices
            for mc in item.get("multiple_choices", []):
                doc = ReadingMultipleChoiceModel(passage_id=passage, **mc)
                await doc.insert()

        return {
            "status": "success",
            "message": f"🌱 Successfully seeded {inserted_count} Reading Passages and their questions!"
        }