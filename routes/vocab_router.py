from fastapi import APIRouter
from classes.Vocabulary import (
    VocabularyCollectionResponse,
    UpdateWordStatusRequest,
    UpdateCollectionProgressRequest,
    VocabularyProgressResponse
)

router = APIRouter()

@router.get(path="/collections/{collection_id}", response_model=VocabularyCollectionResponse)
async def get_vocabulary_collection(collection_id: str):
    """Lấy thông tin bộ từ vựng và danh sách từ kèm IPA, nghĩa, ảnh, ví dụ"""
    pass

@router.post(path="/word-status/update", response_model=VocabularyProgressResponse)
async def update_word_status(payload: UpdateWordStatusRequest):
    """Cập nhật trạng thái từng từ khi học Flashcard (LEARNING, MASTERED, NEEDS_REVIEW)"""
    pass

@router.post(path="/collection-progress/update", response_model=VocabularyProgressResponse)
async def update_collection_progress(payload: UpdateCollectionProgressRequest):
    """Cập nhật phần trăm hoàn thành và thời gian học của toàn bộ bộ từ"""
    pass