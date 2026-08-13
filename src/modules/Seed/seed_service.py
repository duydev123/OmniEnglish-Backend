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
    ListeningAudioSegmentModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)
from .reading_mock import MOCK_READING_PASSAGES
from .listening_mock import MOCK_LISTENING_PASSAGES


from models.Speaking import (
    SpeakingTopicModel,
    SpeakingPromptModel,
    UserSpeakingTestSessionModel,
    ShadowingSentenceModel
)
from .speaking_mock import MOCK_SPEAKING_DATA
from .shadowing_mock import MOCK_SHADOWING_DATA
class SeedService:
    async def seed_reading_only(self) -> dict:
        """Seed dữ liệu Reading"""
        # (original reading implementation is unchanged, we just need to keep this placeholder / structure)

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
            if not isinstance(item, dict):
                continue
            passage_data = item.get("passage")
            if not isinstance(passage_data, dict):
                continue
            passage = ReadingPassageModel(**passage_data)
            await passage.insert()
            inserted_count += 1
            stats["passages"] += 1

            # Insert Multiple Choices
            for mc in item.get("multiple_choices", []):
                if not isinstance(mc, dict):
                    continue
                doc = ReadingMultipleChoiceModel(passage_id=passage, **mc)
                await doc.insert()
                stats["multiple_choices"] += 1

            # Insert Heading Matchings
            for heading in item.get("heading_matchings", []):
                if not isinstance(heading, dict):
                    continue
                doc = ReadingHeadingMatchingModel(passage_id=passage, **heading)
                await doc.insert()
                stats["heading_matchings"] += 1

            # Insert Fill Blanks
            for fill in item.get("fill_blanks", []):
                if not isinstance(fill, dict):
                    continue
                doc = ReadingFillBlankModel(passage_id=passage, **fill)
                await doc.insert()
                stats["fill_blanks"] += 1

            # Insert True/False/Not Given
            for tfng in item.get("true_false_not_given", []):
                if not isinstance(tfng, dict):
                    continue
                doc = ReadingTrueFalseNotGivenModel(passage_id=passage, **tfng)
                await doc.insert()
                stats["true_false_not_given"] += 1

        return {
            "status": "success",
            "message": f"🌱 Successfully seeded {inserted_count} Reading Passages and their questions!"
        }

    # ==========================================
    # SEED LISTENING (THÊM MỚI)
    # ==========================================
    async def seed_listening_only(self) -> dict:
        """Seed dữ liệu Listening"""
        # 1. Xóa sạch dữ liệu cũ
        await ListeningPassageModel.delete_all()
        await ListeningAudioSegmentModel.delete_all()
        await ListeningMultipleChoiceModel.delete_all()
        await ListeningCompletionModel.delete_all()
        await UserListeningSessionModel.delete_all()

        inserted_count = 0
        stats = {
            "passages": 0,
            "audio_segments": 0,
            "multiple_choices": 0,
            "completions": 0
        }
        
        # 2. Loop qua danh sách Passage mock và lưu vào DB
        for item in MOCK_LISTENING_PASSAGES:
            if not isinstance(item, dict):
                continue
            passage_data = item.get("passage")
            if not isinstance(passage_data, dict):
                continue
            passage = ListeningPassageModel(**passage_data)
            await passage.insert()
            inserted_count += 1
            stats["passages"] += 1

            # Insert Audio Segments first
            segment_key_to_doc = {}
            for seg in item.get("audio_segments", []):
                if not isinstance(seg, dict):
                    continue
                key = seg.pop("key", None)
                doc = ListeningAudioSegmentModel(passage_id=passage, **seg)
                await doc.insert()
                stats["audio_segments"] += 1
                if key:
                    segment_key_to_doc[key] = doc

            # Insert Multiple Choices
            for mc in item.get("multiple_choices", []):
                if not isinstance(mc, dict):
                    continue
                audio_key = mc.pop("audio_segment_key", None)
                audio_seg = segment_key_to_doc.get(audio_key) if audio_key else None
                doc = ListeningMultipleChoiceModel(
                    passage_id=passage,
                    audio_segment_id=audio_seg,
                    **mc
                )
                await doc.insert()
                stats["multiple_choices"] += 1

            # Insert Completions
            for comp in item.get("completions", []):
                if not isinstance(comp, dict):
                    continue
                audio_key = comp.pop("audio_segment_key", None)
                audio_seg = segment_key_to_doc.get(audio_key) if audio_key else None
                doc = ListeningCompletionModel(
                    passage_id=passage,
                    audio_segment_id=audio_seg,
                    **comp
                )
                await doc.insert()
                stats["completions"] += 1

        return {
            "status": "success",
            "message": f"🌱 Successfully seeded {inserted_count} Listening Passages!",
            "stats": stats
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
            if not isinstance(item, dict):
                continue
            topic_data = item.get("topic")
            if not isinstance(topic_data, dict):
                continue
            # Tạo Topic
            topic_doc = SpeakingTopicModel(**topic_data)
            await topic_doc.insert()
            inserted_count["topics"] += 1

            # Tạo Prompts (Liên kết với Topic vừa tạo)
            prompts = item.get("prompts", [])
            if isinstance(prompts, list):
                for prompt_data in prompts:
                    if not isinstance(prompt_data, dict):
                        continue
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
            if not isinstance(item, dict):
                continue
            doc = ShadowingSentenceModel(**item)
            await doc.insert()
            inserted_count += 1
            
        return {
            "status": "success",
            "message": f"Successfully seeded {inserted_count} Shadowing Sentences!"
        }