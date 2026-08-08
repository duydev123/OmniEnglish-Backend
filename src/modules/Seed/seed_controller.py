from fastapi import APIRouter, HTTPException, status
from .seed_service import SeedService
from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingTrueFalseNotGivenModel,
    ReadingFillBlankModel
)
from models.Listening import (
    ListeningPassageModel,
    ListeningAudioSegmentModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)
from .listening_mock import MOCK_LISTENING_PASSAGES
from .reading_mock import (
    MOCK_READING_PASSAGES,
    # MOCK_HEADING_MATCHINGS,
    # MOCK_FILL_BLANKS,
    # MOCK_TRUE_FALSE_NOT_GIVEN
)

router = APIRouter()
seed_service = SeedService ()

@router.post("/seed-reading-passages")
async def seed_reading_passages():
    # 0. Xóa sạch dữ liệu cũ để tránh trùng lặp
    await ReadingPassageModel.delete_all()
    await ReadingMultipleChoiceModel.delete_all()
    await ReadingHeadingMatchingModel.delete_all()
    await ReadingFillBlankModel.delete_all()
    await ReadingTrueFalseNotGivenModel.delete_all()
    
    results = []
    
    for mock_data in MOCK_READING_PASSAGES:
        # 1. Tạo passage
        passage_data = mock_data["passage"]
        passage = ReadingPassageModel(**passage_data)
        await passage.insert()
        
        # 4. Tạo multiple choices
        for mc_data in mock_data.get("multiple_choices", []):
            mc = ReadingMultipleChoiceModel(
                passage_id=passage,
                **mc_data
            )
            await mc.insert()
        # 5. Tạo heading matchings
        for heading_data in mock_data.get("heading_matchings", []):
            heading = ReadingHeadingMatchingModel(
                passage_id=passage,
                **heading_data
            )
            await heading.insert()
        
        # 6. Tạo fill blanks
        for fill_data in mock_data.get("fill_blanks", []):
            fill = ReadingFillBlankModel(
                passage_id=passage,
                **fill_data
            )
            await fill.insert()
        
        # 7. Tạo true/false/not given
        for tfng_data in mock_data.get("true_false_not_given", []):
            tfng = ReadingTrueFalseNotGivenModel(
                passage_id=passage,
                **tfng_data
            )
            await tfng.insert()
        results.append({
            "title": passage.title,
            "passage_id": str(passage.id),
            "total_questions": passage.total_questions
        })
    
    return {
        "message": f"Seeded {len(results)} reading passages",
        "data": results
    }

@router.post("/seed-listening-passages")
async def seed_listening_passages():
    """Seed tất cả dữ liệu Listening (Passage + câu hỏi)"""
    try:
        # Xóa dữ liệu cũ
        await ListeningPassageModel.delete_all()
        await ListeningAudioSegmentModel.delete_all()
        await ListeningMultipleChoiceModel.delete_all()
        await ListeningCompletionModel.delete_all()
        await UserListeningSessionModel.delete_all()
        
        results = []
        stats = {
            "passages": 0,
            "audio_segments": 0,
            "multiple_choices": 0,
            "completions": 0
        }
        
        for mock_data in MOCK_LISTENING_PASSAGES:
            # 1. Tạo passage
            passage_data = mock_data["passage"]
            passage = ListeningPassageModel(**passage_data)
            await passage.insert()
            stats["passages"] += 1

            # 2. Tạo audio segments
            segment_key_to_doc = {}
            for seg_data in mock_data.get("audio_segments", []):
                key = seg_data.pop("key", None)
                seg = ListeningAudioSegmentModel(
                    passage_id=passage,
                    **seg_data
                )
                await seg.insert()
                stats["audio_segments"] += 1
                if key:
                    segment_key_to_doc[key] = seg
            
            # 3. Tạo multiple choices
            for mc_data in mock_data.get("multiple_choices", []):
                audio_key = mc_data.pop("audio_segment_key", None)
                audio_seg = segment_key_to_doc.get(audio_key) if audio_key else None
                mc = ListeningMultipleChoiceModel(
                    passage_id=passage,
                    audio_segment_id=audio_seg,
                    **mc_data
                )
                await mc.insert()
                stats["multiple_choices"] += 1
            
            # 4. Tạo completions
            for comp_data in mock_data.get("completions", []):
                audio_key = comp_data.pop("audio_segment_key", None)
                audio_seg = segment_key_to_doc.get(audio_key) if audio_key else None
                comp = ListeningCompletionModel(
                    passage_id=passage,
                    audio_segment_id=audio_seg,
                    **comp_data
                )
                await comp.insert()
                stats["completions"] += 1
            
            results.append({
                "title": passage.title,
                "passage_id": str(passage.id),
                "total_questions": passage.total_questions
            })
        
        return {
            "status": "success",
            "message": f"🌱 Seeded {len(results)} listening passages with all question types!",
            "stats": stats,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# @router.post("/seed-reading-headings")
# async def seed_reading_headings():
#     results = []
#     for mock_data in MOCK_HEADING_MATCHINGS:
#         passage = await ReadingPassageModel.find_one(
#             ReadingPassageModel.title == mock_data["passage_title"]
#         )
#         if not passage:
#             continue
        
#         heading_match = ReadingHeadingMatchingModel(
#             passage_id=passage,
#             order=4,
#             headings=mock_data["headings"],
#             correct_matches=mock_data["correct_matches"]
#         )
#         await heading_match.insert()
#         results.append({
#             "title": mock_data["passage_title"], 
#             "id": str(heading_match.id)
#         })
    
#     return {
#         "message": f"Seeded {len(results)} heading matching records", 
#         "data": results
#     }
# @router.post("/seed-reading-fillblanks")
# async def seed_reading_fillblanks():
#     results = []
#     for mock_data in MOCK_FILL_BLANKS:
#         passage = await ReadingPassageModel.find_one(
#             ReadingPassageModel.title == mock_data["passage_title"]
#         )
#         if not passage:
#             continue
        
#         fill_blank = ReadingFillBlankModel(
#             passage_id=passage,
#             order=5,  # Hoặc order tự động
#             passage_text=mock_data["passage_text"],
#             blanks=mock_data["blanks"],
#             case_sensitive=mock_data["case_sensitive"]
#         )
#         await fill_blank.insert()
#         results.append({"title": mock_data["passage_title"], "id": str(fill_blank.id)})
    
#     return {"message": f"Seeded {len(results)} fill-in-the-blank records", "data": results}
# @router.post("/seed-reading-tfng")
# async def seed_reading_true_false_not_given():
#     try:
#         results = []
#         for mock_data in MOCK_TRUE_FALSE_NOT_GIVEN:
#             passage = await ReadingPassageModel.find_one(
#                 ReadingPassageModel.title == mock_data["passage_title"]
#             )
#             if not passage:
#                 continue
            
#             tfng = ReadingTrueFalseNotGivenModel(
#                 passage_id=passage,
#                 order=6,  # Hoặc order tự động
#                 statements=mock_data["statements"]
#             )
#             await tfng.insert()
#             results.append({
#                 "title": mock_data["passage_title"],
#                 "id": str(tfng.id),
#                 "total_statements": len(mock_data["statements"])
#             })
        
#         return {
#             "message": f"Seeded {len(results)} True/False/Not Given records",
#             "data": results
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed():
    return await seed_service.seed_reading_only()