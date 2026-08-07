import os
import sys
import json
import asyncio
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from beanie import init_beanie, PydanticObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Ensure backend src directory is in Python path for module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)
if os.path.exists(os.path.join(parent_dir, "src")):
    sys.path.insert(0, os.path.join(parent_dir, "src"))

from models.VocabularyCollectionModel import VocabularyCollectionModel, UserWordStatusModel, UserProgressModel
from models.Paragraph import WordModel, WordType

from modules.Vocabulary.vocab_controller import (
    router,
    normalize_word_type,
    validate_object_id,
    format_collection_response,
    get_current_user_id,
)
from modules.Vocabulary.vocab_service import VocabService, fetch_ipa_for_word
from modules.Vocabulary.Vocabulary_dto import (
    PasteTextRequest,
    VocabularyCollectionResponse,
    WordDetailResponse,
    UpdateWordStatusRequest,
    UpdateCollectionProgressRequest,
    VocabularyProgressResponse,
    CreateCollectionRequest,
    UpdateCollectionRequest,
    AddWordRequest,
    UpdateWordRequest,
    BulkAddWordsRequest,
    BulkUpdateWordsRequest,
    BulkUpdateWordItem,
)

# Fixture to initialize Beanie ODM with a mocked database for document field mappings
@pytest.fixture(autouse=True, scope="session")
def init_mock_beanie():
    async def _init():
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={'ok': 1, 'version': '5.0.0'})
        mock_db.name = 'test_db'

        mock_collection = MagicMock()
        mock_collection.index_information = AsyncMock(return_value={})
        mock_collection.create_index = AsyncMock()
        mock_collection.create_indexes = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection

        await init_beanie(
            database=mock_db,
            document_models=[VocabularyCollectionModel, UserWordStatusModel, UserProgressModel, WordModel]
        )

    asyncio.run(_init())


# Create TestClient instance for router integration tests
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# =====================================================================
# SECTION 1: HELPER FUNCTIONS TESTS
# =====================================================================

class TestNormalizeWordType:
    """Test suite for normalize_word_type function."""

    @pytest.mark.parametrize(
        "input_val, expected_output",
        [
            (None, WordType.NOUN.value),
            ("", WordType.NOUN.value),
            ("   ", WordType.NOUN.value),
            ("noun", "noun"),
            ("NOUN", "noun"),
            ("  VERB  ", "verb"),
            ("vErB", "verb"),
            ("AdJeCtIvE", "adjective"),
            ("ADVERB", "adverb"),
            ("phrasal verb", "phrasal verb"),
            ("PHRASAL VERB", "phrasal verb"),
            ("idiom", "idiom"),
            ("IDIOM", "idiom"),
            ("pronoun", "pronoun"),
            ("PRONOUN", "pronoun"),
            ("preposition", "preposition"),
            ("PREPOSITION", "preposition"),
            ("conjunction", "conjunction"),
            ("CONJUNCTION", "conjunction"),
            ("interjection", "interjection"),
            ("INTERJECTION", "interjection"),
            ("invalid_word_type", WordType.NOUN.value),
            ("12345", WordType.NOUN.value),
            ("unknown_type", WordType.NOUN.value),
        ],
    )
    def test_normalize_word_type_multiple_inputs_outputs(self, input_val, expected_output):
        result = normalize_word_type(input_val)
        assert result == expected_output, f"Failed for '{input_val}'"


class TestValidateObjectId:
    """Test suite for validate_object_id function."""

    @pytest.mark.parametrize(
        "input_id, should_succeed, expected_str",
        [
            ("507f1f77bcf86cd799439011", True, "507f1f77bcf86cd799439011"),
            ("60c72b2f9b1d8b0015f8e4a1", True, "60c72b2f9b1d8b0015f8e4a1"),
            ("000000000000000000000000", True, "000000000000000000000000"),
            ("ffffffffffffffffffffffff", True, "ffffffffffffffffffffffff"),
            ("invalid-object-id", False, None),
            ("12345", False, None),
            ("507f1f77bcf86cd79943901g", False, None),
            ("", False, None),
            ("   ", False, None),
            ("507f1f77bcf86cd79943901", False, None),
        ],
    )
    def test_validate_object_id_multiple_inputs_outputs(self, input_id, should_succeed, expected_str):
        if should_succeed:
            result = validate_object_id(input_id)
            assert isinstance(result, PydanticObjectId)
            assert str(result) == expected_str
        else:
            with pytest.raises(HTTPException) as exc_info:
                validate_object_id(input_id)
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Vocabulary collection not found"


class TestFormatCollectionResponse:
    """Test suite for format_collection_response function."""

    def test_format_collection_response_with_words_and_custom_words(self):
        async def run_test():
            mock_collection = MagicMock()
            mock_collection.id = PydanticObjectId("507f1f77bcf86cd799439011")
            mock_collection.title = "IELTS Vocab"
            mock_collection.description = "IELTS words"
            mock_collection.topic = "Education"
            mock_collection.language = "en-US"
            mock_collection.is_official = True
            mock_collection.total_learners = 50
            mock_collection.accuracy_percentage = 90.0
            mock_collection.study_time_seconds = 600

            word1 = MagicMock()
            word1.id = PydanticObjectId("507f1f77bcf86cd799439022")
            word1.word = "apple"
            word1.word_type = "noun"
            word1.meaning = "quả táo"
            word1.ipa = "/ˈæp.əl/"
            word1.example_sentence = "An apple a day."
            word1.image_url = "http://example.com/apple.png"

            link1 = MagicMock()
            link1.fetch = AsyncMock(return_value=word1)

            word2 = MagicMock()
            word2.id = PydanticObjectId("507f1f77bcf86cd799439033")
            word2.word = "run"
            word2.word_type = "verb"
            word2.meaning = "chạy"
            word2.ipa = "/rʌn/"
            word2.example_sentence = "He runs fast."
            word2.image_url = ""

            link2 = MagicMock()
            link2.fetch = AsyncMock(return_value=word2)

            mock_collection.custom_words = [link1]
            mock_collection.words = [link2]

            res = await format_collection_response(mock_collection)
            assert isinstance(res, VocabularyCollectionResponse)
            assert res.id == "507f1f77bcf86cd799439011"
            assert len(res.words_list) == 2
            assert res.words_list[0].word == "apple"
            assert res.words_list[1].word == "run"

        asyncio.run(run_test())


class TestGetCurrentUserId:
    """Test suite for get_current_user_id function."""

    def test_get_current_user_id_returns_expected_user_id(self):
        user_id = get_current_user_id()
        assert user_id == "test_user_123"


# =====================================================================
# SECTION 2: DTO SCHEMA VALIDATIONS TESTS
# =====================================================================

class TestFetchIpaForWord:
    """Test suite for fetch_ipa_for_word function."""

    @patch("modules.Vocabulary.vocab_service.urllib.request.urlopen")
    def test_fetch_ipa_from_dictionary_api(self, mock_urlopen):
        async def run_test():
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps([
                {"phonetics": [{"text": "/ˈæp.əl/"}]}
            ]).encode("utf-8")
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            ipa = await fetch_ipa_for_word("apple")
            assert ipa == "/ˈæp.əl/"

        asyncio.run(run_test())

    def test_fetch_ipa_empty_word_returns_empty_string(self):
        async def run_test():
            ipa = await fetch_ipa_for_word("")
            assert ipa == ""

        asyncio.run(run_test())


class TestVocabularyDTOs:
    """Test suite for schema validations across all Vocabulary DTOs."""

    def test_word_detail_response_defaults(self):
        dto = WordDetailResponse(id="w1", word="hello", word_type="noun")
        assert dto.learning_status == "LEARNING"

    def test_create_collection_request_valid_and_invalid(self):
        valid = CreateCollectionRequest(title="My List", description="Desc", language="en-US")
        assert valid.title == "My List"

        with pytest.raises(ValidationError):
            CreateCollectionRequest(title="")

    def test_update_collection_request_optional_fields(self):
        req = UpdateCollectionRequest(title="Updated Title")
        assert req.title == "Updated Title"
        assert req.description is None
        assert req.language is None

    def test_add_word_request_validation(self):
        req = AddWordRequest(word="ubiquitous", word_type="adjective", meaning="phổ biến")
        assert req.word == "ubiquitous"
        assert req.meaning == "phổ biến"

    def test_update_word_request_validation(self):
        req = UpdateWordRequest(word="new_word", ipa="/new/")
        assert req.word == "new_word"
        assert req.ipa == "/new/"

    def test_bulk_add_words_request_validation(self):
        item = AddWordRequest(word="hello", word_type="noun", meaning="xin chào")
        req = BulkAddWordsRequest(words=[item])
        assert len(req.words) == 1
        assert req.words[0].word == "hello"

    def test_bulk_update_words_request_validation(self):
        item = BulkUpdateWordItem(id="507f1f77bcf86cd799439011", word="updated")
        req = BulkUpdateWordsRequest(words=[item])
        assert len(req.words) == 1
        assert req.words[0].word == "updated"

    def test_paste_text_request_validation(self):
        req = PasteTextRequest(raw_text="This is a test paragraph.")
        assert req.raw_text == "This is a test paragraph."

        with pytest.raises(ValidationError):
            PasteTextRequest(raw_text="")

    def test_update_word_status_request_validation(self):
        valid = UpdateWordStatusRequest(collection_id="507f1f77bcf86cd799439011", word_id="w1", status="MASTERED")
        assert valid.status == "MASTERED"

        with pytest.raises(ValidationError):
            UpdateWordStatusRequest(collection_id="507f1f77bcf86cd799439011", word_id="w1", status="INVALID_STATUS")

    def test_update_collection_progress_request_validation(self):
        valid = UpdateCollectionProgressRequest(collection_id="507f1f77bcf86cd799439011", accuracy_percentage=80.0, study_time_seconds=120)
        assert valid.accuracy_percentage == 80.0

        with pytest.raises(ValidationError):
            UpdateCollectionProgressRequest(collection_id="507f1f77bcf86cd799439011", accuracy_percentage=150.0, study_time_seconds=120)

        with pytest.raises(ValidationError):
            UpdateCollectionProgressRequest(collection_id="507f1f77bcf86cd799439011", accuracy_percentage=80.0, study_time_seconds=-10)


# =====================================================================
# SECTION 3: VOCAB SERVICE METHOD TESTS
# =====================================================================

class TestVocabServiceMethods:
    """Test suite for all static methods in VocabService."""

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.find")
    def test_get_my_collections(self, mock_find):
        async def run_test():
            mock_col = MagicMock()
            mock_col.id = PydanticObjectId("507f1f77bcf86cd799439011")
            mock_col.title = "Personal"
            mock_col.description = "Personal collection"
            mock_col.topic = "Custom"
            mock_col.language = "en-US"
            mock_col.is_official = False
            mock_col.total_learners = 1
            mock_col.custom_words = []
            mock_col.words = []

            mock_query = MagicMock()
            mock_query.to_list = AsyncMock(return_value=[mock_col])
            mock_find.return_value = mock_query

            res = await VocabService.get_my_collections()
            assert len(res) == 1
            assert res[0].title == "Personal"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.find")
    def test_get_official_collections(self, mock_find):
        async def run_test():
            mock_col = MagicMock()
            mock_col.id = PydanticObjectId("507f1f77bcf86cd799439011")
            mock_col.title = "Official IELTS"
            mock_col.description = "Official collection"
            mock_col.topic = "IELTS"
            mock_col.language = "en-US"
            mock_col.is_official = True
            mock_col.total_learners = 100
            mock_col.custom_words = []
            mock_col.words = []

            mock_query = MagicMock()
            mock_query.to_list = AsyncMock(return_value=[mock_col])
            mock_find.return_value = mock_query

            res = await VocabService.get_official_collections()
            assert len(res) == 1
            assert res[0].is_official is True

        asyncio.run(run_test())

    @patch.object(VocabularyCollectionModel, "insert", new_callable=AsyncMock)
    def test_create_my_collection(self, mock_insert):
        async def run_test():
            payload = CreateCollectionRequest(title="New List", description="Desc", language="en-US")
            res = await VocabService.create_my_collection(payload)
            assert isinstance(res, VocabularyCollectionResponse)
            assert res.title == "New List"
            assert res.is_official is False

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_update_collection_details_success(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.id = PydanticObjectId("507f1f77bcf86cd799439011")
            mock_col.title = "Old Title"
            mock_col.is_official = False
            mock_col.save = AsyncMock()
            mock_get.return_value = mock_col

            payload = UpdateCollectionRequest(title="New Title")
            res = await VocabService.update_collection_details("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"
            assert res["title"] == "New Title"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_update_collection_details_official_raises_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col

            payload = UpdateCollectionRequest(title="New Title")
            with pytest.raises(HTTPException) as exc:
                await VocabService.update_collection_details("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403

        asyncio.run(run_test())

    @patch.object(WordModel, "insert", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_add_word_to_collection(self, mock_get, mock_word_insert):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = []
            mock_col.save = AsyncMock()
            mock_get.return_value = mock_col

            payload = AddWordRequest(word="innovative", word_type="adjective", meaning="sáng tạo")
            res = await VocabService.add_word_to_collection("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"
            assert "innovative" in res["message"]

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.WordModel.get")
    def test_update_single_word_success(self, mock_word_get):
        async def run_test():
            mock_word = MagicMock()
            mock_word.id = PydanticObjectId("507f1f77bcf86cd799439022")
            mock_word.word = "old_word"
            mock_word.word_type = "noun"
            mock_word.meaning = "old_meaning"
            mock_word.ipa = ""
            mock_word.example_sentence = ""
            mock_word.image_url = ""
            mock_word.save = AsyncMock()
            mock_word_get.return_value = mock_word

            payload = UpdateWordRequest(word="new_word", meaning="new_meaning")
            res = await VocabService.update_single_word("507f1f77bcf86cd799439022", payload)
            assert res["status"] == "success"
            assert res["word"] == "new_word"
            assert res["meaning"] == "new_meaning"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.WordModel.get")
    def test_update_single_word_not_found_raises_404(self, mock_word_get):
        async def run_test():
            mock_word_get.return_value = None
            payload = UpdateWordRequest(word="word")
            with pytest.raises(HTTPException) as exc:
                await VocabService.update_single_word("507f1f77bcf86cd799439022", payload)
            assert exc.value.status_code == 404

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.WordModel.get")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_bulk_update_words_in_collection(self, mock_col_get, mock_word_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            w1 = MagicMock()
            w1.save = AsyncMock()
            mock_word_get.return_value = w1

            item = BulkUpdateWordItem(id="507f1f77bcf86cd799439022", word="updated_bulk")
            payload = BulkUpdateWordsRequest(words=[item])
            res = await VocabService.bulk_update_words_in_collection("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"

        asyncio.run(run_test())

    @patch.object(WordModel, "insert", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_bulk_add_words_to_collection(self, mock_col_get, mock_word_insert):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = []
            mock_col.save = AsyncMock()
            mock_col_get.return_value = mock_col

            item = AddWordRequest(word="bulk1", word_type="noun", meaning="m1")
            payload = BulkAddWordsRequest(words=[item])
            res = await VocabService.bulk_add_words_to_collection("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_process_and_add_pasted_text_too_long_raises_400(self, mock_col_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            long_text = "a" * 5001
            payload = PasteTextRequest(raw_text=long_text)
            with pytest.raises(HTTPException) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 400

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.genai.Client")
    @patch.object(WordModel, "find_one", new_callable=AsyncMock)
    @patch.object(WordModel, "insert", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_process_and_add_pasted_text_with_gemini_success(
        self, mock_col_get, mock_word_insert, mock_word_find_one, mock_genai_client
    ):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = []
            mock_col.save = AsyncMock()
            mock_col_get.return_value = mock_col

            mock_word_find_one.return_value = None

            mock_response = MagicMock()
            mock_response.text = json.dumps([
                {
                    "word": "resilience",
                    "word_type": "noun",
                    "cefr_level": "B2",
                    "topic": "General",
                    "meaning": "sự kiên cường",
                    "ipa": "/rɪˈzɪl.jəns/",
                    "example_sentence": "She showed resilience."
                }
            ])

            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_client_instance

            payload = PasteTextRequest(raw_text="She showed resilience during tough times.")
            res = await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"
            assert res["added_count"] == 1
            assert "resilience" in res["extracted_words"]

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_get_vocabulary_collection_success(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.id = PydanticObjectId("507f1f77bcf86cd799439011")
            mock_col.title = "Collection 1"
            mock_col.description = "Desc"
            mock_col.topic = "General"
            mock_col.language = "en-US"
            mock_col.is_official = True
            mock_col.total_learners = 10
            mock_col.custom_words = []
            mock_col.words = []

            mock_get.return_value = mock_col

            res = await VocabService.get_vocabulary_collection("507f1f77bcf86cd799439011")
            assert isinstance(res, VocabularyCollectionResponse)
            assert res.id == "507f1f77bcf86cd799439011"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_get_vocabulary_collection_not_found_raises_404(self, mock_get):
        async def run_test():
            mock_get.return_value = None
            with pytest.raises(HTTPException) as exc:
                await VocabService.get_vocabulary_collection("507f1f77bcf86cd799439011")
            assert exc.value.status_code == 404

        asyncio.run(run_test())

    @patch.object(UserProgressModel, "find_one", new_callable=AsyncMock)
    @patch.object(UserWordStatusModel, "find")
    @patch.object(UserWordStatusModel, "find_one", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_update_word_status_existing_record(
        self, mock_col_get, mock_status_find_one, mock_status_find, mock_progress_find_one
    ):
        async def run_test():
            mock_col = MagicMock()
            mock_col.custom_words = [1]
            mock_col.words = []
            mock_col_get.return_value = mock_col

            existing_record = MagicMock()
            existing_record.save = AsyncMock()
            mock_status_find_one.return_value = existing_record

            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=1)
            mock_status_find.return_value = mock_query

            existing_user_prog = MagicMock()
            existing_user_prog.save = AsyncMock()
            mock_progress_find_one.return_value = existing_user_prog

            payload = UpdateWordStatusRequest(collection_id="507f1f77bcf86cd799439011", word_id="w1", status="MASTERED")
            res = await VocabService.update_word_status(payload)
            assert isinstance(res, VocabularyProgressResponse)
            assert res.total_mastered == 1
            assert res.accuracy_percentage == 100.0

        asyncio.run(run_test())

    @patch.object(UserProgressModel, "find_one", new_callable=AsyncMock)
    @patch.object(UserWordStatusModel, "find")
    @patch.object(UserWordStatusModel, "find_one", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_update_collection_progress(
        self, mock_col_get, mock_status_find_one, mock_status_find, mock_progress_find_one
    ):
        async def run_test():
            mock_col = MagicMock()
            mock_col.custom_words = [1, 2]
            mock_col.words = []
            mock_col_get.return_value = mock_col

            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=1)
            mock_status_find.return_value = mock_query

            existing_user_prog = MagicMock()
            existing_user_prog.study_time_seconds = 100
            existing_user_prog.save = AsyncMock()
            mock_progress_find_one.return_value = existing_user_prog

            payload = UpdateCollectionProgressRequest(
                collection_id="507f1f77bcf86cd799439011", accuracy_percentage=50.0, study_time_seconds=60
            )
            res = await VocabService.update_collection_progress(payload)
            assert isinstance(res, VocabularyProgressResponse)
            assert res.total_mastered == 1
            assert res.accuracy_percentage == 50.0

        asyncio.run(run_test())

    @patch.object(UserProgressModel, "find")
    @patch.object(UserWordStatusModel, "find")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_delete_vocabulary_collection_success(self, mock_col_get, mock_status_find, mock_prog_find):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = []
            mock_col.delete = AsyncMock()
            mock_col_get.return_value = mock_col

            mock_status_query = MagicMock()
            mock_status_query.delete = AsyncMock()
            mock_status_find.return_value = mock_status_query

            mock_prog_query = MagicMock()
            mock_prog_query.delete = AsyncMock()
            mock_prog_find.return_value = mock_prog_query

            res = await VocabService.delete_vocabulary_collection("507f1f77bcf86cd799439011")
            assert res["status"] == "success"

        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_delete_vocabulary_collection_official_raises_403(self, mock_col_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_col_get.return_value = mock_col

            with pytest.raises(HTTPException) as exc:
                await VocabService.delete_vocabulary_collection("507f1f77bcf86cd799439011")
            assert exc.value.status_code == 403

        asyncio.run(run_test())


# =====================================================================
# SECTION 4: CONTROLLER API ROUTE INTEGRATION TESTS
# =====================================================================

class TestVocabControllerRoutes:
    """Integration test suite for all FastAPI routes in vocab_controller via TestClient."""

    @patch.object(VocabService, "get_my_collections", new_callable=AsyncMock)
    def test_get_my_collections_route(self, mock_service):
        mock_service.return_value = [
            VocabularyCollectionResponse(
                id="507f1f77bcf86cd799439011",
                title="My Vocab",
                description="Desc",
                topic="Custom",
                language="en-US",
                is_official=False,
                total_learners=1,
                accuracy_percentage=0.0,
                study_time_seconds=0,
                words_list=[]
            )
        ]
        response = client.get("/collections/my-collections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "My Vocab"

    @patch.object(VocabService, "get_official_collections", new_callable=AsyncMock)
    def test_get_official_collections_route(self, mock_service):
        mock_service.return_value = [
            VocabularyCollectionResponse(
                id="507f1f77bcf86cd799439011",
                title="Official IELTS",
                description="Desc",
                topic="IELTS",
                language="en-US",
                is_official=True,
                total_learners=100,
                accuracy_percentage=0.0,
                study_time_seconds=0,
                words_list=[]
            )
        ]
        response = client.get("/collections/official")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_official"] is True

    @patch.object(VocabService, "create_my_collection", new_callable=AsyncMock)
    def test_create_my_collection_route(self, mock_service):
        mock_service.return_value = VocabularyCollectionResponse(
            id="507f1f77bcf86cd799439011",
            title="New List",
            description="Desc",
            topic="Custom",
            language="en-US",
            is_official=False,
            total_learners=1,
            accuracy_percentage=0.0,
            study_time_seconds=0,
            words_list=[]
        )
        response = client.post(
            "/collections/my-collections",
            json={"title": "New List", "description": "Desc", "language": "en-US"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New List"

    @patch.object(VocabService, "update_collection_details", new_callable=AsyncMock)
    def test_update_collection_details_route(self, mock_service):
        mock_service.return_value = {
            "status": "success",
            "message": "Successfully updated collection 'Updated Title'!",
            "id": "507f1f77bcf86cd799439011",
            "title": "Updated Title",
            "description": "Desc",
            "language": "en-US"
        }
        response = client.put(
            "/collections/507f1f77bcf86cd799439011",
            json={"title": "Updated Title"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @patch.object(VocabService, "add_word_to_collection", new_callable=AsyncMock)
    def test_add_word_to_collection_route(self, mock_service):
        mock_service.return_value = {"status": "success", "message": "Successfully added word 'apple'!"}
        response = client.post(
            "/collections/507f1f77bcf86cd799439011/words",
            json={"word": "apple", "word_type": "noun", "meaning": "quả táo"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch.object(VocabService, "update_single_word", new_callable=AsyncMock)
    def test_update_single_word_route(self, mock_service):
        mock_service.return_value = {
            "status": "success",
            "message": "Successfully updated word 'apple'!",
            "id": "507f1f77bcf86cd799439022",
            "word": "apple",
            "word_type": "noun",
            "meaning": "táo thơm",
            "ipa": "/apple/",
            "example_sentence": "",
            "image_url": ""
        }
        response = client.put(
            "/words/507f1f77bcf86cd799439022",
            json={"meaning": "táo thơm"}
        )
        assert response.status_code == 200
        assert response.json()["word"] == "apple"

    @patch.object(VocabService, "bulk_update_words_in_collection", new_callable=AsyncMock)
    def test_bulk_update_words_in_collection_route(self, mock_service):
        mock_service.return_value = {"status": "success", "message": "Successfully updated 1 words in bulk!"}
        response = client.put(
            "/collections/507f1f77bcf86cd799439011/words/bulk-update",
            json={"words": [{"id": "507f1f77bcf86cd799439022", "word": "updated"}]}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch.object(VocabService, "bulk_add_words_to_collection", new_callable=AsyncMock)
    def test_bulk_add_words_to_collection_route(self, mock_service):
        mock_service.return_value = {"status": "success", "message": "Successfully bulk added 1 words!"}
        response = client.post(
            "/collections/507f1f77bcf86cd799439011/words/bulk",
            json={"words": [{"word": "bulk1", "word_type": "noun", "meaning": "m1"}]}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch.object(VocabService, "process_and_add_pasted_text_with_gemini", new_callable=AsyncMock)
    def test_process_and_add_pasted_text_route(self, mock_service):
        mock_service.return_value = {
            "status": "success",
            "message": "Gemini AI success",
            "added_count": 1,
            "new_created_count": 1,
            "highlighted_text": "**resilience**",
            "extracted_words": ["resilience"]
        }
        response = client.post(
            "/collections/507f1f77bcf86cd799439011/words/paste-text",
            json={"raw_text": "resilience in action"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch.object(VocabService, "get_vocabulary_collection", new_callable=AsyncMock)
    def test_get_vocabulary_collection_route(self, mock_service):
        mock_service.return_value = VocabularyCollectionResponse(
            id="507f1f77bcf86cd799439011",
            title="My List",
            description="Desc",
            topic="Custom",
            language="en-US",
            is_official=False,
            total_learners=1,
            accuracy_percentage=0.0,
            study_time_seconds=0,
            words_list=[]
        )
        response = client.get("/collections/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["id"] == "507f1f77bcf86cd799439011"

    @patch.object(VocabService, "update_word_status", new_callable=AsyncMock)
    def test_update_word_status_route(self, mock_service):
        mock_service.return_value = VocabularyProgressResponse(
            message="Progress updated",
            user_id="test_user_123",
            collection_id="507f1f77bcf86cd799439011",
            total_mastered=1,
            total_learning=0,
            accuracy_percentage=100.0
        )
        response = client.post(
            "/word-status/update",
            json={"collection_id": "507f1f77bcf86cd799439011", "word_id": "w1", "status": "MASTERED"}
        )
        assert response.status_code == 200
        assert response.json()["accuracy_percentage"] == 100.0

    @patch.object(VocabService, "update_collection_progress", new_callable=AsyncMock)
    def test_update_collection_progress_route(self, mock_service):
        mock_service.return_value = VocabularyProgressResponse(
            message="Progress updated",
            user_id="test_user_123",
            collection_id="507f1f77bcf86cd799439011",
            total_mastered=1,
            total_learning=0,
            accuracy_percentage=50.0
        )
        response = client.post(
            "/collection-progress/update",
            json={"collection_id": "507f1f77bcf86cd799439011", "accuracy_percentage": 50.0, "study_time_seconds": 120}
        )
        assert response.status_code == 200
        assert response.json()["accuracy_percentage"] == 50.0

    @patch.object(VocabService, "delete_vocabulary_collection", new_callable=AsyncMock)
    def test_delete_vocabulary_collection_route(self, mock_service):
        mock_service.return_value = {"status": "success", "message": "Collection deleted successfully!"}
        response = client.delete("/collections/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch.object(VocabService, "get_my_collections", new_callable=AsyncMock)
    def test_controller_handles_500_error(self, mock_service):
        mock_service.side_effect = Exception("Database error")
        response = client.get("/collections/my-collections")
        assert response.status_code == 500
        assert "Unknown server error" in response.json()["detail"]


# =====================================================================
# SECTION 5: COMPREHENSIVE USER ERROR HANDLING TESTS (Lỗi từ người dùng)
# =====================================================================

class TestVocabUserErrorHandling:
    """
    Test suite for checking user-induced errors:
    - Invalid ObjectId format in paths
    - Attempting forbidden modifications on Official Collections (403)
    - Duplicate Word Additions (409)
    - Payload Schema Validation Errors (422)
    - Input Length Limits (400)
    - Resource Not Found (404)
    """

    @pytest.mark.parametrize(
        "endpoint, method, payload",
        [
            ("/collections/invalid_id", "GET", None),
            ("/collections/invalid_id", "PUT", {"title": "Updated"}),
            ("/collections/invalid_id/words", "POST", {"word": "apple", "word_type": "noun", "meaning": "táo"}),
            ("/words/invalid_id", "PUT", {"word": "apple"}),
            ("/collections/invalid_id/words/bulk-update", "PUT", {"words": []}),
            ("/collections/invalid_id/words/bulk", "POST", {"words": []}),
            ("/collections/invalid_id/words/paste-text", "POST", {"raw_text": "sample text"}),
            ("/collections/invalid_id", "DELETE", None),
        ],
    )
    def test_invalid_object_id_returns_404_across_routes(self, endpoint, method, payload):
        if method == "GET":
            response = client.get(endpoint)
        elif method == "PUT":
            response = client.put(endpoint, json=payload)
        elif method == "POST":
            response = client.post(endpoint, json=payload)
        elif method == "DELETE":
            response = client.delete(endpoint)
        assert response.status_code == 404
        assert response.json()["detail"] == "Vocabulary collection not found"

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_update_official_collection_details_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            payload = UpdateCollectionRequest(title="New Title")
            with pytest.raises(HTTPException) as exc:
                await VocabService.update_collection_details("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403
            assert "permission" in exc.value.detail or "not found" in exc.value.detail
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_add_word_to_official_collection_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            payload = AddWordRequest(word="book", word_type="noun", meaning="sách")
            with pytest.raises(HTTPException) as exc:
                await VocabService.add_word_to_collection("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_bulk_update_words_in_official_collection_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            payload = BulkUpdateWordsRequest(words=[])
            with pytest.raises(HTTPException) as exc:
                await VocabService.bulk_update_words_in_collection("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_bulk_add_words_to_official_collection_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            payload = BulkAddWordsRequest(words=[])
            with pytest.raises(HTTPException) as exc:
                await VocabService.bulk_add_words_to_collection("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_paste_text_to_official_collection_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            payload = PasteTextRequest(raw_text="Sample text")
            with pytest.raises(HTTPException) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 403
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_delete_official_collection_returns_403(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = True
            mock_get.return_value = mock_col
            with pytest.raises(HTTPException) as exc:
                await VocabService.delete_vocabulary_collection("507f1f77bcf86cd799439011")
            assert exc.value.status_code == 403
            assert "official" in exc.value.detail
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_add_duplicate_word_same_type_raises_409(self, mock_get):
        async def run_test():
            existing_w = MagicMock()
            existing_w.word = "apple"
            existing_w.word_type = "noun"

            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = [existing_w]
            mock_col.fetch_link = AsyncMock()
            mock_get.return_value = mock_col

            payload = AddWordRequest(word="apple", word_type="noun", meaning="quả táo")
            with pytest.raises(HTTPException) as exc:
                await VocabService.add_word_to_collection("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 409
            assert "apple" in exc.value.detail
            assert "đã tồn tại" in exc.value.detail
        asyncio.run(run_test())

    @patch.object(WordModel, "insert", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_add_same_word_different_type_succeeds(self, mock_get, mock_word_insert):
        async def run_test():
            existing_w = MagicMock()
            existing_w.word = "run"
            existing_w.word_type = "noun"

            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = [existing_w]
            mock_col.fetch_link = AsyncMock()
            mock_col.save = AsyncMock()
            mock_get.return_value = mock_col

            # Adding 'run' as a verb should be allowed
            payload = AddWordRequest(word="run", word_type="verb", meaning="chạy")
            res = await VocabService.add_word_to_collection("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"
        asyncio.run(run_test())

    @patch.object(WordModel, "insert", new_callable=AsyncMock)
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_bulk_add_words_skips_duplicates_and_returns_summary(self, mock_get, mock_word_insert):
        async def run_test():
            existing_w = MagicMock()
            existing_w.word = "apple"
            existing_w.word_type = "noun"

            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col.custom_words = [existing_w]
            mock_col.fetch_link = AsyncMock()
            mock_col.save = AsyncMock()
            mock_get.return_value = mock_col

            item_dup = AddWordRequest(word="apple", word_type="noun", meaning="quả táo")
            item_new = AddWordRequest(word="banana", word_type="noun", meaning="quả chuối")
            payload = BulkAddWordsRequest(words=[item_dup, item_new])

            res = await VocabService.bulk_add_words_to_collection("507f1f77bcf86cd799439011", payload)
            assert res["status"] == "success"
            assert res["added_count"] == 1
            assert len(res["skipped_words"]) == 1
            assert "apple (noun)" in res["skipped_words"]
        asyncio.run(run_test())

    def test_pydantic_payload_validation_errors_return_422(self):
        # 1. Missing required title when creating collection
        resp = client.post("/collections/my-collections", json={})
        assert resp.status_code == 422

        # 2. Empty raw_text when pasting text
        resp = client.post("/collections/507f1f77bcf86cd799439011/words/paste-text", json={"raw_text": ""})
        assert resp.status_code == 422

        # 3. Invalid status value for word status update
        resp = client.post(
            "/word-status/update",
            json={"collection_id": "507f1f77bcf86cd799439011", "word_id": "w1", "status": "NOT_A_STATUS"}
        )
        assert resp.status_code == 422

        # 4. Negative study_time_seconds for collection progress
        resp = client.post(
            "/collection-progress/update",
            json={"collection_id": "507f1f77bcf86cd799439011", "accuracy_percentage": 50.0, "study_time_seconds": -5}
        )
        assert resp.status_code == 422

        # 5. Accuracy percentage > 100
        resp = client.post(
            "/collection-progress/update",
            json={"collection_id": "507f1f77bcf86cd799439011", "accuracy_percentage": 150.0, "study_time_seconds": 10}
        )
        assert resp.status_code == 422

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_paste_text_exceeds_max_length_raises_400(self, mock_get):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_get.return_value = mock_col

            long_text = "a" * 5001
            payload = PasteTextRequest(raw_text=long_text)
            with pytest.raises(HTTPException) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert exc.value.status_code == 400
            assert "too long" in exc.value.detail.lower()
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_get_non_existent_collection_raises_404(self, mock_get):
        async def run_test():
            mock_get.return_value = None
            with pytest.raises(HTTPException) as exc:
                await VocabService.get_vocabulary_collection("507f1f77bcf86cd799439011")
            assert exc.value.status_code == 404
            assert exc.value.detail == "Vocabulary collection not found"
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.WordModel.get")
    def test_update_non_existent_single_word_raises_404(self, mock_get):
        async def run_test():
            mock_get.return_value = None
            payload = UpdateWordRequest(word="word")
            with pytest.raises(HTTPException) as exc:
                await VocabService.update_single_word("507f1f77bcf86cd799439022", payload)
            assert exc.value.status_code == 404
            assert exc.value.detail == "Word not found"
        asyncio.run(run_test())


# =====================================================================
# SECTION 6: COMPREHENSIVE SYSTEM & THIRD-PARTY ERROR TESTS (Lỗi hệ thống)
# =====================================================================

class TestVocabSystemErrorHandling:
    """
    Test suite for checking system and 3rd-party integration errors:
    - Gemini API 503 / Unavailable retries & error propagation
    - Gemini API empty / malformed / unexpected response structures
    - Network timeouts and failures in external IPA lookups
    - Recursion depth guards in phrase IPA generation
    - Automatic 500 error mapping in controller for unhandled service exceptions
    """

    @patch("modules.Vocabulary.vocab_service.genai.Client")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_gemini_503_unavailable_retries_and_raises_exception(self, mock_col_get, mock_genai_client):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content.side_effect = Exception("503 Service Unavailable")
            mock_genai_client.return_value = mock_client_instance

            payload = PasteTextRequest(raw_text="This is a test sentence for Gemini 503 error handling.")
            with pytest.raises(Exception) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert "503 Service Unavailable" in str(exc.value)
            # Verify it retried 3 times
            assert mock_client_instance.models.generate_content.call_count == 3
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.genai.Client")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_gemini_returns_empty_response_raises_value_error(self, mock_col_get, mock_genai_client):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            mock_response = MagicMock()
            mock_response.text = ""
            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_client_instance

            payload = PasteTextRequest(raw_text="This is a test sentence.")
            with pytest.raises(ValueError) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert "Gemini returned empty response" in str(exc.value)
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.genai.Client")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_gemini_returns_invalid_json_raises_json_decode_error(self, mock_col_get, mock_genai_client):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            mock_response = MagicMock()
            mock_response.text = "Not a valid JSON array string"
            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_client_instance

            payload = PasteTextRequest(raw_text="This is a test sentence.")
            with pytest.raises(json.JSONDecodeError):
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.genai.Client")
    @patch("modules.Vocabulary.vocab_service.VocabularyCollectionModel.get")
    def test_gemini_returns_unexpected_json_structure_raises_value_error(self, mock_col_get, mock_genai_client):
        async def run_test():
            mock_col = MagicMock()
            mock_col.is_official = False
            mock_col_get.return_value = mock_col

            mock_response = MagicMock()
            mock_response.text = "12345"  # Valid JSON integer, but unexpected type
            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_client_instance

            payload = PasteTextRequest(raw_text="This is a test sentence.")
            with pytest.raises(ValueError) as exc:
                await VocabService.process_and_add_pasted_text_with_gemini("507f1f77bcf86cd799439011", payload)
            assert "Unexpected response format" in str(exc.value)
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.httpx.AsyncClient.get")
    def test_fetch_ipa_handles_httpx_network_timeout(self, mock_httpx_get):
        async def run_test():
            mock_httpx_get.side_effect = httpx.TimeoutException("Connection timed out")
            ipa = await fetch_ipa_for_word("timeoutword")
            assert ipa == ""
        asyncio.run(run_test())

    @patch("modules.Vocabulary.vocab_service.httpx.AsyncClient.get")
    def test_fetch_ipa_handles_httpx_500_server_error(self, mock_httpx_get):
        async def run_test():
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Internal Error", request=MagicMock(), response=mock_resp
            )
            mock_httpx_get.return_value = mock_resp

            ipa = await fetch_ipa_for_word("servererrorword")
            assert ipa == ""
        asyncio.run(run_test())

    def test_fetch_ipa_exceeds_max_recursion_depth_returns_empty(self):
        async def run_test():
            ipa = await fetch_ipa_for_word("test phrase", depth=3)
            assert ipa == ""
        asyncio.run(run_test())

    @pytest.mark.parametrize(
        "route, method, payload",
        [
            ("/collections/official", "GET", None),
            ("/collections/my-collections", "POST", {"title": "Test List"}),
            ("/collections/507f1f77bcf86cd799439011", "PUT", {"title": "Update"}),
            ("/collections/507f1f77bcf86cd799439011/words", "POST", {"word": "a", "word_type": "noun", "meaning": "m"}),
            ("/words/507f1f77bcf86cd799439022", "PUT", {"word": "a"}),
            ("/collections/507f1f77bcf86cd799439011/words/bulk-update", "PUT", {"words": []}),
            ("/collections/507f1f77bcf86cd799439011/words/bulk", "POST", {"words": []}),
            ("/collections/507f1f77bcf86cd799439011/words/paste-text", "POST", {"raw_text": "sample text"}),
            ("/collections/507f1f77bcf86cd799439011", "GET", None),
            ("/word-status/update", "POST", {"collection_id": "507f1f77bcf86cd799439011", "word_id": "w1", "status": "MASTERED"}),
            ("/collection-progress/update", "POST", {"collection_id": "507f1f77bcf86cd799439011", "accuracy_percentage": 50.0, "study_time_seconds": 60}),
            ("/collections/507f1f77bcf86cd799439011", "DELETE", None),
        ],
    )
    def test_all_controller_routes_handle_service_exceptions_returning_500(self, route, method, payload):
        # Patch all corresponding methods in VocabService to raise unexpected Exception
        service_methods = {
            "/collections/official": "get_official_collections",
            "/collections/my-collections": "create_my_collection",
            "/collections/507f1f77bcf86cd799439011": "update_collection_details" if method == "PUT" else ("get_vocabulary_collection" if method == "GET" else "delete_vocabulary_collection"),
            "/collections/507f1f77bcf86cd799439011/words": "add_word_to_collection",
            "/words/507f1f77bcf86cd799439022": "update_single_word",
            "/collections/507f1f77bcf86cd799439011/words/bulk-update": "bulk_update_words_in_collection",
            "/collections/507f1f77bcf86cd799439011/words/bulk": "bulk_add_words_to_collection",
            "/collections/507f1f77bcf86cd799439011/words/paste-text": "process_and_add_pasted_text_with_gemini",
            "/word-status/update": "update_word_status",
            "/collection-progress/update": "update_collection_progress",
        }
        method_name = service_methods[route]

        with patch.object(VocabService, method_name, new_callable=AsyncMock) as mock_service:
            mock_service.side_effect = Exception("Unexpected Database/System Error")
            if method == "GET":
                response = client.get(route)
            elif method == "PUT":
                response = client.put(route, json=payload)
            elif method == "POST":
                response = client.post(route, json=payload)
            elif method == "DELETE":
                response = client.delete(route)

            assert response.status_code == 500
            assert "detail" in response.json()

