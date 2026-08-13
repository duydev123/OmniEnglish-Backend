import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from modules.User.user_util import UserUtil
from .Vocabulary_dto import (
    PasteTextRequest,
    VocabularyCollectionResponse,
    UpdateWordStatusRequest,
    UpdateCollectionProgressRequest,
    VocabularyProgressResponse,
    CreateCollectionRequest,
    UpdateCollectionRequest,
    AddWordRequest,
    UpdateWordRequest,
    BulkAddWordsRequest,
    BulkUpdateWordsRequest
)
from .vocab_service import (
    VocabService,
    normalize_word_type,
    get_current_user_id,
    validate_object_id,
    format_collection_response,
    fetch_ipa_for_word,
    fetch_word_details
)
from core.mock_registry import mock_registry

logger = logging.getLogger(__name__)
router = APIRouter()


def extract_user_id(current_user: dict) -> str:
    if not current_user:
        return ""
    return str(current_user.get("_id") or current_user.get("id") or "")


@router.get(path="/fetch-ipa")
async def fetch_ipa_endpoint(word: str):
    """Fetch standard IPA phonetic transcription and primary word_type for a word via backend"""
    try:
        return await fetch_word_details(word)
    except Exception as e:
        logger.error(f"Error fetching IPA and word_type for {word}: {str(e)}")
        return {"word": word, "ipa": "", "word_type": "noun"}



# =====================================================================
# COLLECTION ROUTES
# =====================================================================

@router.get(path="/collections/my-collections", response_model=List[VocabularyCollectionResponse])
async def get_my_collections(current_user: dict = Depends(UserUtil.Protect)):
    """Get all personal user vocabulary collections from MongoDB for the authenticated user"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.get_my_collections(user_id=user_id)
    except Exception as e:
        logger.error(f"Error fetching my collections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.get(path="/collections/official", response_model=List[VocabularyCollectionResponse])
async def get_official_collections(current_user: Optional[dict] = Depends(UserUtil.ProtectOptional)):
    """Get all official system default vocabulary collections from MongoDB"""
    try:
        user_id = extract_user_id(current_user) if current_user else None
        return await VocabService.get_official_collections(user_id=user_id)
    except Exception as e:
        logger.error(f"Error fetching official collections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/collections/seed-ielts-idioms", response_model=VocabularyCollectionResponse)
async def seed_ielts_idioms_collection():
    """Seed the 100+ IELTS Idioms Master Collection into MongoDB"""
    try:
        return await VocabService.seed_ielts_idioms_collection()
    except Exception as e:
        logger.error(f"Error seeding IELTS idioms collection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(path="/collections/my-collections", response_model=VocabularyCollectionResponse)
async def create_my_collection(payload: CreateCollectionRequest, current_user: dict = Depends(UserUtil.Protect)):
    """Create a new personal vocabulary collection (is_official = False) for authenticated user"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.create_my_collection(payload=payload, user_id=user_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/collections/{collection_id}")
async def update_collection_details(
    collection_id: str, 
    payload: UpdateCollectionRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Update details (title, description, language) of a personal collection"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.update_collection_details(collection_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words")
async def add_word_to_collection(
    collection_id: str, 
    payload: AddWordRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Add a new word to a specific collection"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.add_word_to_collection(collection_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/words/{word_id}")
async def update_single_word(
    word_id: str, 
    payload: UpdateWordRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Update details of an existing word"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.update_single_word(word_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/collections/{collection_id}/words/bulk-update")
async def bulk_update_words_in_collection(
    collection_id: str, 
    payload: BulkUpdateWordsRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Bulk update multiple words inside a specific collection"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.bulk_update_words_in_collection(collection_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words/bulk")
async def bulk_add_words_to_collection(
    collection_id: str, 
    payload: BulkAddWordsRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Receive an array of words, validate and insert them individually to generate exact Links"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.bulk_add_words_to_collection(collection_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words/paste-text")
async def process_and_add_pasted_text_with_gemini(
    collection_id: str, 
    payload: PasteTextRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """
    Use Google Gemini AI to analyze raw text and extract high-value vocabulary words.
    Filters out common stop words and categorizes words by CEFR and Parts of Speech.
    """
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.process_and_add_pasted_text_with_gemini(collection_id, payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


# =====================================================================
# PROGRESS & STATUS API ROUTES
# =====================================================================

@router.get(path="/collections/{collection_id}", response_model=VocabularyCollectionResponse)
async def get_vocabulary_collection(
    collection_id: str, 
    current_user: Optional[dict] = Depends(UserUtil.ProtectOptional)
):
    """Get vocabulary collection details including word list with IPA, meaning, image, and examples"""
    try:
        user_id = extract_user_id(current_user) if current_user else None
        return await VocabService.get_vocabulary_collection(collection_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection {collection_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/word-status/update", response_model=VocabularyProgressResponse)
async def update_word_status(
    payload: UpdateWordStatusRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Update individual word status during Flashcard study (LEARNING, MASTERED, NEEDS_REVIEW)"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.update_word_status(payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating word status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/collection-progress/update", response_model=VocabularyProgressResponse)
async def update_collection_progress(
    payload: UpdateCollectionProgressRequest, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Update completion percentage and study time for the entire collection"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.update_collection_progress(payload, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating collection progress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.delete(path="/collections/{collection_id}")
async def delete_vocabulary_collection(
    collection_id: str, 
    current_user: dict = Depends(UserUtil.Protect)
):
    """Delete a personal vocabulary collection and its associated progress data"""
    try:
        user_id = extract_user_id(current_user)
        return await VocabService.delete_vocabulary_collection(collection_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection {collection_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")
