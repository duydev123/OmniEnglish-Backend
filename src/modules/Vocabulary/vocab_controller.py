import os
import json
import time
import logging 
from datetime import UTC, datetime, timezone
from typing import Optional, List

from beanie import PydanticObjectId 
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types

from models.VocabularyCollectionModel import (
    VocabularyCollectionModel, 
    UserWordStatusModel, 
    UserProgressModel, 
    WordLearningStatus
)
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
from models.Paragraph import WordModel

logger = logging.getLogger(__name__)
router = APIRouter()

# =====================================================================
# AUTHENTICATION HELPER
# =====================================================================

def get_current_user_id() -> str:
    """
    TODO: Replace with actual JWT decoding logic later.
    (e.g., retrieving from a global request context or middleware)
    """
    return "test_user_123"


def validate_object_id(id_str: str) -> PydanticObjectId:
    if not PydanticObjectId.is_valid(id_str):
        raise HTTPException(status_code=404, detail="Vocabulary collection not found")
    return PydanticObjectId(id_str)


# Helper function to format collection model to response DTO
async def format_collection_response(collection: VocabularyCollectionModel) -> VocabularyCollectionResponse:
    words_list = []
    
    if hasattr(collection, 'custom_words') and collection.custom_words:
        for link in collection.custom_words:
            word = await link.fetch() if hasattr(link, 'fetch') else link 
            if word:
                words_list.append({
                    "id": str(word.id),
                    "word": word.word,
                    "word_type": word.word_type,
                    "meaning": word.meaning,
                    "ipa": getattr(word, "ipa", ""),
                    "example_sentence": getattr(word, "example_sentence", ""),
                    "image_url": getattr(word, "image_url", "")
                })
                
    if hasattr(collection, 'words') and collection.words:
        for link in collection.words:
            word = await link.fetch() if hasattr(link, 'fetch') else link
            if word:
                words_list.append({
                    "id": str(word.id),
                    "word": word.word,
                    "word_type": word.word_type,
                    "meaning": word.meaning,
                    "ipa": getattr(word, "ipa", ""),
                    "example_sentence": getattr(word, "example_sentence", ""),
                    "image_url": getattr(word, "image_url", "")
                })

    return VocabularyCollectionResponse(
        id=str(collection.id),
        title=collection.title,
        description=collection.description,
        topic=collection.topic,
        language=collection.language,
        is_official=collection.is_official,
        total_learners=collection.total_learners,
        accuracy_percentage=getattr(collection, 'accuracy_percentage', 0.0),
        study_time_seconds=getattr(collection, 'study_time_seconds', 0),
        words_list=words_list
    )


# =====================================================================
# COLLECTION ROUTES
# =====================================================================

@router.get(path="/collections/my-collections", response_model=List[VocabularyCollectionResponse])
async def get_my_collections():
    """Get all personal user vocabulary collections from MongoDB"""
    try:
        collections = await VocabularyCollectionModel.find(VocabularyCollectionModel.is_official == False).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col)
            res.append(formatted)
        return res
    except Exception as e:
        logger.error(f"Error fetching my collections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.get(path="/collections/official", response_model=List[VocabularyCollectionResponse])
async def get_official_collections():
    """Get all official system default vocabulary collections from MongoDB"""
    try:
        collections = await VocabularyCollectionModel.find(VocabularyCollectionModel.is_official == True).to_list()
        res = []
        for col in collections:
            formatted = await format_collection_response(col)
            res.append(formatted)
        return res
    except Exception as e:
        logger.error(f"Error fetching official collections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/collections/my-collections", response_model=VocabularyCollectionResponse)
async def create_my_collection(payload: CreateCollectionRequest):
    """Create a new personal vocabulary collection (is_official = False)"""
    try:
        new_collection = VocabularyCollectionModel(
            title=payload.title,
            description=payload.description,
            language=payload.language,
            topic="Custom",
            is_official=False,
            is_public=False,
            total_learners=1,
            words=[],
            custom_words=[]
        )
        await new_collection.insert()

        return VocabularyCollectionResponse(
            id=str(new_collection.id),
            title=new_collection.title,
            description=new_collection.description,
            topic=new_collection.topic,
            language=new_collection.language,
            is_official=new_collection.is_official,
            total_learners=new_collection.total_learners,
            accuracy_percentage=0.0,
            study_time_seconds=0,
            words_list=[]
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/collections/{collection_id}")
async def update_collection_details(collection_id: str, payload: UpdateCollectionRequest):
    """Update details (title, description, language) of a personal collection"""
    try:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        if payload.title is not None:
            collection.title = payload.title
        if payload.description is not None:
            collection.description = payload.description
        if payload.language is not None:
            collection.language = payload.language

        await collection.save()

        return {
            "status": "success",
            "message": f"Successfully updated collection '{collection.title}'!",
            "id": str(collection.id),
            "title": collection.title,
            "description": collection.description,
            "language": collection.language
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words")
async def add_word_to_collection(collection_id: str, payload: AddWordRequest):
    """Add a new word to a specific collection"""
    try:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        word_type_val = (payload.word_type or "unknown").lower()
        valid_types = ["noun", "verb", "adjective", "adverb", "phrasal verb", "idiom", "pronoun", "preposition", "conjunction", "interjection"]
        if word_type_val not in valid_types:
            word_type_val = "noun"
            
        new_word = WordModel(
            word=payload.word,
            word_type=word_type_val,
            meaning=payload.meaning or "Pending update",
            ipa=payload.ipa or "",
            example_sentence=payload.example_sentence or "",
            image_url=payload.image_url or ""
        )
        await new_word.insert()

        collection.custom_words.append(new_word)
        await collection.save()

        return {"status": "success", "message": f"Successfully added the word '{payload.word}'!"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/words/{word_id}")
async def update_single_word(word_id: str, payload: UpdateWordRequest):
    """Update details of an existing word"""
    try:
        obj_id = validate_object_id(word_id)
        word = await WordModel.get(obj_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        if payload.word is not None:
            word.word = payload.word
        if payload.word_type is not None:
            word.word_type = payload.word_type.lower()
        if payload.meaning is not None:
            word.meaning = payload.meaning
        if payload.ipa is not None:
            word.ipa = payload.ipa
        if payload.example_sentence is not None:
            word.example_sentence = payload.example_sentence
        if payload.image_url is not None:
            word.image_url = payload.image_url

        await word.save()

        return {
            "status": "success",
            "message": f"Successfully updated word '{word.word}'!",
            "id": str(word.id),
            "word": word.word,
            "word_type": word.word_type,
            "meaning": word.meaning,
            "ipa": word.ipa,
            "example_sentence": word.example_sentence,
            "image_url": word.image_url
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.put(path="/collections/{collection_id}/words/bulk-update")
async def bulk_update_words_in_collection(collection_id: str, payload: BulkUpdateWordsRequest):
    """Bulk update multiple words inside a specific collection"""
    try:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        updated_count = 0
        for item in payload.words:
            if not PydanticObjectId.is_valid(item.id):
                continue
            word_obj = await WordModel.get(PydanticObjectId(item.id))
            if word_obj:
                if item.word is not None:
                    word_obj.word = item.word
                if item.word_type is not None:
                    word_obj.word_type = item.word_type.lower()
                if item.meaning is not None:
                    word_obj.meaning = item.meaning
                if item.ipa is not None:
                    word_obj.ipa = item.ipa
                if item.example_sentence is not None:
                    word_obj.example_sentence = item.example_sentence
                if item.image_url is not None:
                    word_obj.image_url = item.image_url
                await word_obj.save()
                updated_count += 1

        return {
            "status": "success",
            "message": f"Successfully updated {updated_count} words in bulk!"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words/bulk")
async def bulk_add_words_to_collection(collection_id: str, payload: BulkAddWordsRequest):
    """Receive an array of words, validate and insert them individually to generate exact Links"""
    try:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        new_words_objects = []
        
        for w in payload.words:
            word_type_val = w.word_type.lower() if w.word_type and w.word_type != "Select..." else "noun"
            
            new_word = WordModel(
                word=w.word,
                word_type=word_type_val,
                meaning=w.meaning,
                ipa=w.ipa or "",
                example_sentence=w.example_sentence or "",
                image_url=w.image_url or ""
            )
            
            await new_word.insert()
            new_words_objects.append(new_word)
            collection.custom_words.append(new_word)

        if new_words_objects:
            await collection.save()

        return {
            "status": "success", 
            "message": f"Successfully bulk added {len(new_words_objects)} words!"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


@router.post(path="/collections/{collection_id}/words/paste-text")
async def process_and_add_pasted_text_with_gemini(collection_id: str, payload: PasteTextRequest):
    """
    Use Google Gemini AI to analyze raw text and extract high-value vocabulary words.
    Filters out common stop words and categorizes words by CEFR and Parts of Speech.
    """
    try:
        user_id = get_current_user_id() 
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection or collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="Collection not found or you do not have permission to edit it"
            )

        MAX_TEXT_LENGTH = 5000
        if len(payload.raw_text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text is too long ({len(payload.raw_text)} characters). Please edit it to be under {MAX_TEXT_LENGTH} characters."
            )

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Enhanced & Optimized Gemini Prompt
        prompt = f"""
        Act as an expert English lexicographer and language tutor. Analyze the following English text and extract up to 15-20 key vocabulary words or phrasal verbs that are most valuable for a Vietnamese English learner to study.

        CRITICAL SELECTION RULES:
        1. Ignore basic/common stop words (e.g. "the", "and", "they", "is", "have", "go", "make", "good").
        2. Prioritize academic, professional, B1-C2 CEFR level words, useful phrasal verbs, or domain-specific terms.
        3. Convert verbs to their base/infinitive form (e.g. "analyzed" -> "analyze").

        For each word, provide:
        - "word": The base English word or phrasal verb.
        - "word_type": One of exactly [noun, verb, adjective, adverb, phrasal verb, idiom, pronoun, preposition, conjunction]
        - "cefr_level": One of [A1, A2, B1, B2, C1, C2]
        - "topic": Appropriate topic category (e.g. Technology, Business, Education, Environment, Daily Life)
        - "meaning": Concise, natural, contextually accurate Vietnamese translation.
        - "ipa": Standard IPA transcription with slashes (e.g. /rɪˈzɪl.jəns/).
        - "example_sentence": A clear, natural English example sentence demonstrating the word in context.

        OUTPUT FORMAT:
        Return ONLY a raw valid JSON array of objects. Do NOT use markdown codeblock wrappers like ```json.

        Text to analyze:
        {payload.raw_text}
        """

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=8192
                    ),
                )
                break
            except Exception as api_err:
                err_str = str(api_err)
                if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise api_err

        if not response or not response.text:
            raise ValueError("Gemini returned empty response")
        
        raw_output = response.text.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        extracted_data = json.loads(raw_output)
        if isinstance(extracted_data, dict):
            extracted_data = [extracted_data]
        elif not isinstance(extracted_data, list):
            raise ValueError("Unexpected response format")        
        
        new_words_objects = []
        added_words = set()
        collection_updated = False 

        for item in extracted_data:
            word_val = item.get("word")
            if not word_val or word_val in added_words:
                continue
            
            existing_word = await WordModel.find_one(WordModel.word == word_val)
            
            if existing_word:
                is_in_collection = any(
                    getattr(link, 'ref', None) and link.ref.id == existing_word.id 
                    for link in collection.custom_words
                )
                
                if not is_in_collection:
                    collection.custom_words.append(existing_word)
                    collection_updated = True 
                
                added_words.add(word_val)
                continue
            
            word_type_val = (item.get("word_type") or "noun").lower()
            valid_types = ["noun", "verb", "adjective", "adverb", "phrasal verb", "idiom", "pronoun", "preposition", "conjunction"]
            if word_type_val not in valid_types:
                word_type_val = "noun"
            
            cefr_val = (item.get("cefr_level") or "B1").upper()
            valid_cefr = ["A1", "A2", "B1", "B2", "C1", "C2"]
            if cefr_val not in valid_cefr:
                cefr_val = "B1"
            
            new_word = WordModel(
                word=word_val,
                word_type=word_type_val,
                cefr_level=cefr_val,
                topic=item.get("topic", "General"),
                meaning=item.get("meaning", ""),
                ipa=item.get("ipa", ""),
                example_sentence=item.get("example_sentence", ""),
                image_url="",
                user_id=user_id,
            )
            
            await new_word.insert()
            new_words_objects.append(new_word)
            collection.custom_words.append(new_word)
            added_words.add(word_val)
            collection_updated = True 

        if collection_updated:
            await collection.save()

        highlighted_text = payload.raw_text
        for item in extracted_data:
            word = item.get("word")
            if word and word in highlighted_text:
                highlighted_text = highlighted_text.replace(word, f"**{word}**")

        return {
            "status": "success",
            "message": f"Gemini AI đã phân tích văn bản thành công! (Tạo mới {len(new_words_objects)} từ, thêm tổng cộng {len(added_words)} từ vào bộ).",
            "added_count": len(added_words),
            "new_created_count": len(new_words_objects),
            "highlighted_text": highlighted_text,
            "extracted_words": list(added_words)
        }

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error parsing data from AI. Please try again.")
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) or "Unknown Server Error")


# =====================================================================
# PROGRESS & STATUS API ROUTES
# =====================================================================

@router.get(path="/collections/{collection_id}", response_model=VocabularyCollectionResponse)
async def get_vocabulary_collection(collection_id: str):
    """Get vocabulary collection details including word list with IPA, meaning, image, and examples"""
    try:
        obj_id = validate_object_id(collection_id)
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        return await format_collection_response(collection)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection {collection_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/word-status/update", response_model=VocabularyProgressResponse)
async def update_word_status(payload: UpdateWordStatusRequest):
    """Update individual word status during Flashcard study (LEARNING, MASTERED, NEEDS_REVIEW)"""
    try:
        user_id = get_current_user_id() 
        collection_id = payload.collection_id
        obj_id = validate_object_id(collection_id)

        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
            
        progress_record = await UserWordStatusModel.find_one(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.word == payload.word_id
        )

        if progress_record:
            progress_record.status = payload.status
            progress_record.last_reviewed_at = datetime.now(UTC)
            await progress_record.save()
        else:
            new_progress = UserWordStatusModel(
                user_id=user_id,
                collection_id=collection, 
                word=payload.word_id,
                status=payload.status,
                last_reviewed_at=datetime.now(UTC)
            )
            await new_progress.insert()

        total_mastered = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.MASTERED
        ).count()
        
        total_learning = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.LEARNING
        ).count()

        total_words_in_collection = len(collection.custom_words) + len(collection.words)
        accuracy = (total_mastered / total_words_in_collection * 100) if total_words_in_collection > 0 else 0.0

        user_progress = await UserProgressModel.find_one(
            UserProgressModel.user_id == user_id,
            UserProgressModel.collection_id.id == obj_id
        )
        
        if user_progress:
            user_progress.accuracy_percentage = accuracy
            user_progress.updated_at = datetime.now(UTC)
            await user_progress.save()
        else:
            new_user_progress = UserProgressModel(
                user_id=user_id,
                collection_id=collection,
                accuracy_percentage=accuracy,
                study_time_seconds=0,
                updated_at=datetime.now(UTC)
            )
            await new_user_progress.insert()

        return VocabularyProgressResponse(
            message="Word progress updated successfully!",
            user_id=user_id,
            collection_id=collection_id,
            total_mastered=total_mastered,
            total_learning=total_learning,
            accuracy_percentage=round(accuracy, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating word status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")


@router.post(path="/collection-progress/update", response_model=VocabularyProgressResponse)
async def update_collection_progress(payload: UpdateCollectionProgressRequest):
    """Update completion percentage and study time for the entire collection"""
    try:
        user_id = get_current_user_id()
        collection_id = payload.collection_id
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        user_progress = await UserProgressModel.find_one(
            UserProgressModel.user_id == user_id,
            UserProgressModel.collection_id.id == obj_id
        )
        
        if user_progress:
            user_progress.study_time_seconds += payload.study_time_seconds
            user_progress.last_studied_at = datetime.now(UTC)
            user_progress.updated_at = datetime.now(UTC)
            await user_progress.save()
        else:
            new_user_progress = UserProgressModel(
                user_id=user_id,
                collection_id=collection, 
                accuracy_percentage=payload.accuracy_percentage,
                study_time_seconds=payload.study_time_seconds,
                last_studied_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            await new_user_progress.insert()
            
        total_mastered = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.MASTERED
        ).count()
        
        total_learning = await UserWordStatusModel.find(
            UserWordStatusModel.user_id == user_id,
            UserWordStatusModel.collection_id.id == obj_id,
            UserWordStatusModel.status == WordLearningStatus.LEARNING
        ).count()
        
        total_words_in_collection = len(collection.custom_words) + len(collection.words)
        backend_accuracy = (total_mastered / total_words_in_collection * 100) if total_words_in_collection > 0 else 0.0

        if user_progress:
            user_progress.accuracy_percentage = backend_accuracy
            await user_progress.save()

        return VocabularyProgressResponse(
            message="Learning progress updated successfully!",
            user_id=user_id,
            collection_id=collection_id,
            total_mastered=total_mastered,
            total_learning=total_learning,
            accuracy_percentage=round(backend_accuracy, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating collection progress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")
    

@router.delete(path="/collections/{collection_id}")
async def delete_vocabulary_collection(collection_id: str):
    """Delete a personal vocabulary collection and its associated progress data"""
    try:
        obj_id = validate_object_id(collection_id)
        
        collection = await VocabularyCollectionModel.get(obj_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Vocabulary collection not found")
        
        if collection.is_official:
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to delete an official system collection"
            )
            
        await UserWordStatusModel.find(
            UserWordStatusModel.collection_id.id == obj_id
        ).delete()
        
        await UserProgressModel.find(
            UserProgressModel.collection_id.id == obj_id
        ).delete()

        if hasattr(collection, 'custom_words') and collection.custom_words:
            for link in collection.custom_words:
                word = await link.fetch() if hasattr(link, 'fetch') else link 
                if word:
                    await word.delete()
                    
        await collection.delete()

        return {
            "status": "success", 
            "message": "Vocabulary collection and associated data deleted successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection {collection_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown server error")