import asyncio
import httpx
import hashlib
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from cachetools import TTLCache
from google import genai
from google.genai import types

logger = logging.getLogger("AIService")


# ============================================================================
# AI Configuration
# ============================================================================
class AIConfig:
    DEFAULT_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    OUTLINE_TEMPERATURE: float = float(os.getenv("AI_OUTLINE_TEMP", "0.2"))
    COLLOCATIONS_TEMPERATURE: float = float(os.getenv("AI_COLLOCATIONS_TEMP", "0.2"))
    SAMPLE_ESSAY_TEMPERATURE: float = float(os.getenv("AI_SAMPLE_ESSAY_TEMP", "0.2"))
    EVALUATION_TEMPERATURE: float = float(os.getenv("AI_EVALUATION_TEMP", "0.1"))
    IMPROVED_SAMPLE_TEMPERATURE: float = float(os.getenv("AI_IMPROVED_SAMPLE_TEMP", "0.2"))
    
    CACHE_TTL: int = int(os.getenv("AI_CACHE_TTL", "3600"))
    CACHE_MAXSIZE: int = int(os.getenv("AI_CACHE_MAXSIZE", "200"))
    MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))
    TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "30"))

    OUTLINE_TIMEOUT: int = int(os.getenv("AI_OUTLINE_TIMEOUT", "15"))
    COLLOCATIONS_TIMEOUT: int = int(os.getenv("AI_COLLOCATIONS_TIMEOUT", "15"))
    SAMPLE_ESSAY_TIMEOUT: int = int(os.getenv("AI_SAMPLE_ESSAY_TIMEOUT", "60"))
    EVALUATION_TIMEOUT: int = int(os.getenv("AI_EVALUATION_TIMEOUT", "25"))
    IMPROVED_SAMPLE_TIMEOUT: int = int(os.getenv("AI_IMPROVED_SAMPLE_TIMEOUT", "25"))

    @classmethod
    def get_api_key(cls) -> str:
        return os.getenv("GEMINI_API_KEY", "")


# ============================================================================
# AI Exceptions
# ============================================================================
class AIError(Exception):
    """Base exception class for AI Service errors"""
    pass

class AIAPIError(AIError):
    """Raised when Gemini API request fails or times out"""
    pass

class AIResponseParseError(AIError):
    """Raised when AI response JSON cannot be decoded or parsed"""
    pass


# ============================================================================
# AI Cache Service
# ============================================================================
class AICacheService:
    def __init__(self, ttl: Optional[int] = None, maxsize: Optional[int] = None):
        ttl = ttl if ttl is not None else AIConfig.CACHE_TTL
        maxsize = maxsize if maxsize is not None else AIConfig.CACHE_MAXSIZE
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def _build_key(
        self,
        prompt_id: str,
        action: str,
        temperature: Optional[float] = None,
        user_notes: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> str:
        key_parts = [prompt_id, action.upper()]
        
        if temperature is not None:
            key_parts.append(f"temp_{temperature}")

        if difficulty is not None:
            key_parts.append(f"diff_{difficulty}") 

        if user_notes:
            if len(user_notes) > 50:
                notes_hash = hashlib.md5(user_notes.encode()).hexdigest()[:8]
                key_parts.append(f"notes_{notes_hash}")
            else:
                key_parts.append(f"notes_{user_notes}")
        
        return ":".join(key_parts)

    def get(
        self,
        prompt_id: str,
        action: str,
        temperature: Optional[float] = None,
        user_notes: Optional[str] = None,
        difficulty: Optional[str] = None 
    ) -> Optional[Any]:
        key = self._build_key(prompt_id, action, temperature, user_notes, difficulty)
        val = self._cache.get(key)
        if val is not None:
            logger.info(f"AICache HIT for key: {key}")
        return val

    def set(
        self,
        prompt_id: str,
        action: str,
        data: Any,
        temperature: Optional[float] = None,
        user_notes: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> None:
        key = self._build_key(prompt_id, action, temperature, user_notes, difficulty)
        self._cache[key] = data
        logger.info(f"AICache SET for key: {key}")


# ============================================================================
# Gemini Response Parser
# ============================================================================
class GeminiResponseParser:
    @staticmethod
    def parse_json_response(raw_text: str, expected_keys: List[str] = None) -> Any:
        if not raw_text or not raw_text.strip():
            raise AIResponseParseError("Empty response text from AI service")

        cleaned_text = raw_text.strip()
        cleaned_text = re.sub(r"^```json\s*", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"^```\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
        cleaned_text = cleaned_text.strip()

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as err:
            logger.error(f"Failed to parse JSON from AI response: {err}. Raw: {raw_text[:200]}")
            raise AIResponseParseError(f"Invalid JSON structure returned by AI: {err}")

        if expected_keys and isinstance(data, dict):
            missing_keys = [key for key in expected_keys if key not in data]
            if missing_keys:
                logger.warning(f"AI response JSON missing expected keys: {missing_keys}")

        return data


# ============================================================================
# AI Response Validator
# ============================================================================
class AIResponseValidator:
    @staticmethod
    def validate_outline(data: Any) -> List[Dict[str, Any]]:
        if not isinstance(data, list):
            logger.warning(f"AI outline response is not a list: {type(data)}")
            return []
        validated = []
        for item in data:
            if isinstance(item, dict):
                validated.append({
                    "title": str(item.get("title", "Section")),
                    "sub_points": [str(sp) for sp in item.get("sub_points", [])] if isinstance(item.get("sub_points"), list) else []
                })
        return validated

    @staticmethod
    def validate_collocations(data: Any) -> List[Dict[str, Any]]:
        if not isinstance(data, list):
            logger.warning(f"AI collocations response is not a list: {type(data)}")
            return []
        
        validated = []
        for group in data:
            if isinstance(group, dict):
                items = group.get("items", [])
                validated_items = []
                
                for item in items:
                    if isinstance(item, dict):
                        # Lấy các giá trị với fallback an toàn
                        word = str(item.get("word", item.get("text", "")))
                        basic_equivalent = str(item.get("basic_equivalent", item.get("basic", "")))
                        
                        # Nếu có "meaning" nhưng không có "meaning_en", dùng "meaning" làm cả 2
                        meaning = item.get("meaning", "")
                        meaning_en = str(item.get("meaning_en", meaning))
                        meaning_vi = str(item.get("meaning_vi", ""))
                        
                        # Nếu meaning_vi trống, tạo từ meaning_en
                        if not meaning_vi and meaning_en:
                            meaning_vi = f"(Cần dịch: {meaning_en})"
                        elif not meaning_vi and not meaning_en:
                            meaning_vi = "Chưa có giải thích"
                        
                        validated_items.append({
                            "word": word,
                            "basic_equivalent": basic_equivalent,
                            "meaning_en": meaning_en or "No meaning provided",
                            "meaning_vi": meaning_vi or "Chưa có giải thích tiếng Việt",
                            "example": str(item.get("example", "No example provided"))
                        })
                    elif isinstance(item, str):
                        validated_items.append({
                            "word": item,
                            "basic_equivalent": "",
                            "meaning_en": "Definition not available",
                            "meaning_vi": "Chưa có giải thích tiếng Việt",
                            "example": "Example not available"
                        })
                    else:
                        validated_items.append({
                            "word": str(item),
                            "basic_equivalent": "",
                            "meaning_en": "Definition not available",
                            "meaning_vi": "Chưa có giải thích tiếng Việt",
                            "example": "Example not available"
                        })
                
                validated.append({
                    "category": str(group.get("category", "General")),
                    "items": validated_items
                })
        
        return validated

    @staticmethod
    def validate_sample_essay(data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            logger.warning(f"AI sample essay response is not a dict: {type(data)}")
            data = {}
        validated = dict(data)
        if 'full_text' not in validated or not validated['full_text']:
            logger.warning("Missing 'full_text' in AI sample essay response, filling default")
            validated['full_text'] = "No essay content generated."
        if 'sample_title' not in validated or not validated['sample_title']:
            logger.warning("Missing 'sample_title' in AI sample essay response, filling default")
            validated['sample_title'] = "Model Essay"
        if 'structure_annotations' not in validated or not isinstance(validated['structure_annotations'], list):
            logger.warning("Missing 'structure_annotations' list in AI sample essay response, filling default")
            validated['structure_annotations'] = [
                {"section": "Introduction", "note": "Clear thesis statement"},
                {"section": "Body 1", "note": "Main supporting argument"},
                {"section": "Body 2", "note": "Secondary supporting argument"},
                {"section": "Conclusion", "note": "Summary of main points"}
            ]
        if 'good_practices' not in validated or not isinstance(validated['good_practices'], list):
            logger.warning("Missing 'good_practices' list in AI sample essay response, filling default")
            validated['good_practices'] = [
                "Academic vocabulary",
                "Clear structure",
                "Formal tone"
            ]

        return validated


# ============================================================================
# Prompt Templates
# ============================================================================
class UltimateIELTSPrompt:
    """Prompt hoàn chỉnh chuẩn IELTS Band 9.0 cho AI LLM Generation System"""

    @staticmethod
    def _format_references_detailed(refs: dict) -> dict:
        """Format references chi tiết hơn cho sample essays, vocabulary, structures, và examples"""
        refs = refs or {}
        
        # Sample essays
        essays = refs.get('sample_essays', [])
        if essays:
            essay_text = "\n\n".join([
                f"**Reference Essay {i+1}** (Band {e.get('band_score', '9.0')})\n"
                f"Topic: {e.get('title', 'N/A')}\n"
                f"Excerpt: {e.get('full_text', '')[:200]}...\n"
                f"Key Strength: {e.get('key_strength', 'Sophisticated academic vocabulary')}"
                for i, e in enumerate(essays[:3])
            ])
        else:
            essay_text = "No sample essays provided. Use your Cambridge examiner expertise to write an exemplary Band 9.0 essay."
        
        # Vocabulary
        vocab = refs.get('vocabulary', [])
        if vocab:
            vocab_text = ", ".join([
                f"**{v.get('word') if isinstance(v, dict) else v}**"
                for v in vocab[:15]
            ])
        else:
            vocab_text = "Use advanced academic Band 9.0 vocabulary appropriate for the task."
        
        # Structures
        structures = refs.get('structures', [])
        if structures:
            struct_text = "\n".join([
                f"- {s.get('section', s.get('name', 'Structure'))}: {s.get('guide', s.get('description', ''))}"
                for s in structures[:5]
            ])
        else:
            struct_text = "Use standard 5-paragraph IELTS academic structure"
        
        # Examples
        examples = refs.get('examples', [])
        if examples:
            example_text = "\n".join([
                f"- {ex.get('source', 'Academic Report')} ({ex.get('date', '2025')}): {ex.get('data', ex)}"
                for ex in examples[:5]
            ])
        else:
            example_text = "Include relevant statistics, academic studies, or real-world data"
        
        return {
            'sample_essays': essay_text,
            'vocabulary': vocab_text,
            'structures': struct_text,
            'examples': example_text
        }


    @staticmethod
    def generate_sample_essay_prompt(
        title: str,
        description: str,
        references: Optional[dict] = None,
        difficulty: str = "medium"  
    ) -> str:
        difficulty_requirements = {
            "easy": """
    **DIFFICULTY: EASY (Band 6-7)**
    - Write a clear, well-structured essay
    - Use accessible vocabulary
    - Simple but effective arguments
    - Word count: 250-265 words (STRICT UPPER LIMIT: 300 words)
    """,
            "medium": """
    **DIFFICULTY: MEDIUM (Band 7-8)**
    - Write a cohesive, academic essay
    - Use varied vocabulary
    - Well-developed arguments with examples
    - Word count: 265-280 words (STRICT UPPER LIMIT: 300 words)
    """,
            "advanced": """
    **DIFFICULTY: ADVANCED (Band 8-9)**
    - Write a sophisticated, nuanced essay
    - Use advanced academic vocabulary
    - Complex arguments with counter-arguments
    - Word count: 280-300 words (STRICT UPPER LIMIT: MUST NOT EXCEED 300 WORDS)
    """
        }
        
        formatted_refs = UltimateIELTSPrompt._format_references_detailed(references or {})
        
        return f"""
    # 🎯 IELTS ESSAY GENERATION SYSTEM

    You are **Professor James Richardson**, a Senior IELTS Examiner.

    {difficulty_requirements.get(difficulty, difficulty_requirements['medium'])}

    **⚠️ STRICT WORD COUNT CONSTRAINT:**
    The generated sample essay MUST NOT exceed 300 words under any circumstances (Target: 250 - 300 words).

    ## 📌 YOUR TASK
    Write a model essay for:
    Topic: {title}
    Task Description: {description}

    ---

    ## 📚 REFERENCE MATERIALS (Use as Inspiration)
    {formatted_refs['sample_essays']}

    ---

    ## 📊 JSON OUTPUT
    Return JSON:
    {{
    "sample_title": "Model Essay: {title}",
    "full_text": "[COMPLETE ESSAY (MAX 300 WORDS)]",
    "word_count": 280,
    "structure_annotations": [
        {{"section": "Introduction", "note": "Clear thesis"}},
        {{"section": "Body 1", "note": "Main argument"}},
        {{"section": "Body 2", "note": "Counter-argument"}},
        {{"section": "Conclusion", "note": "Summary"}}
    ],
    "good_practices": ["Good vocabulary", "Clear structure"]
    }}
    """

    @staticmethod
    def generate_evaluation_prompt(title: str, description: str, essay_content: str) -> str:
        return f"""
You are **Professor James Richardson**, an extremely **STRICT, METICULOUS, and RIGOROUS** Senior IELTS Examiner with 20+ years of experience at Cambridge English Assessment.

**⚠️ STRICT GRADING DIRECTIVES:**
- Be **STRICT and UNFORGIVING**. Do NOT give generous or inflated scores. Real IELTS examiners are demanding.
- Evaluate strictly according to official Cambridge IELTS Public Band Descriptors (Band 1.0 to 9.0).
- **Task Response (25%)**: Deduct points if arguments are repetitive, lack depth, or fail to fully address all parts of the prompt.
- **Coherence & Cohesion (25%)**: Deduct points for repetitive cohesive devices, poor paragraphing, or weak logical progression.
- **Lexical Resource (25%)**: If vocabulary is basic or repetitive (A2/B1/B2), score must NOT exceed 5.5 or 6.0. Award Band 7.5+ ONLY if the student demonstrates natural, sophisticated academic collocations (C1/C2) with rare minor slips.
- **Grammatical Range & Accuracy (25%)**: Deduct points for EVERY grammar, punctuation, subject-verb agreement, tense, or article error.
- **Specific Error Detection**: Identify ALL specific grammatical flaws, awkward phrases, and vocabulary misuses in `specific_errors` and `highlight_spans`.

Topic Title: "{title}"
Task Description: "{description}"

Student Essay:
"{essay_content}"

Return ONLY a raw valid JSON object matching this schema:
{{
  "overall_score": 6.0,
  "potential_score": 7.0,
  "general_summary": "Objective, strict evaluation of student essay strengths and clear weaknesses...",
  "task_achievement_score": 6.0,
  "coherence_cohesion_score": 6.0,
  "lexical_resource_score": 5.5,
  "grammar_accuracy_score": 6.0,
  "specific_errors": [
    {{
      "category": "Grammar",
      "original": "<exact phrase from student essay>",
      "correction": "<corrected phrase>",
      "rule": "<strict explanation of grammar rule broken>"
    }}
  ],
  "highlight_spans": [
    {{ "text": "<exact snippet>", "type": "GRAMMAR", "feedback_index": 0 }}
  ],
  "improvements_comparison": [
    {{ "category": "Grammar", "original": "<original sentence>", "improved": "<improved sentence>" }}
  ],
  "positive_feedback": ["Identified valid points"],
  "actionable_next_steps": ["Key areas requiring rigorous improvement"]
}}
"""

    @staticmethod
    def generate_outline_prompt(title: str, description: str, difficulty: str = "medium") -> str:
        difficulty_requirements = {
            "easy": """
    **DIFFICULTY: EASY (Band 6-7)**
    - Use simple, clear language
    - Basic essay structure with 4 paragraphs
    - Simple thesis and arguments
    """,
            "medium": """
    **DIFFICULTY: MEDIUM (Band 7-8)**
    - Use academic language
    - Standard 5-paragraph structure
    - Clear thesis with developed arguments
    """,
            "advanced": """
    **DIFFICULTY: ADVANCED (Band 8-9)**
    - Use sophisticated academic language
    - Complex 5+ paragraph structure
    - Nuanced thesis with counter-arguments
    """
        }
        
        return f"""
    You are **Professor James Richardson**, a Senior IELTS Examiner.

    {difficulty_requirements.get(difficulty, difficulty_requirements['medium'])}

    Create a structured essay outline for:
    Title: "{title}"
    Task Description: "{description}"

    Provide a structured JSON response with an array of sections:
    [
    {{
        "title": "Introduction",
        "sub_points": ["Hook: ...", "Background: ...", "Thesis Statement: ..."]
    }},
    {{
        "title": "Body Paragraph 1",
        "sub_points": ["Main Idea: ...", "Supporting Evidence: ...", "Impact/Analysis: ..."]
    }},
    {{
        "title": "Body Paragraph 2",
        "sub_points": ["Main Idea: ...", "Counter-argument/Contrast: ...", "Supporting Point: ..."]
    }},
    {{
        "title": "Conclusion",
        "sub_points": ["Summary of main arguments: ...", "Final Thought/Future Outlook: ..."]
    }}
    ]
    Return ONLY raw valid JSON.
    """

    @staticmethod
    def generate_collocations_prompt(title: str, description: str, difficulty: str = "medium") -> str:
        # Định nghĩa yêu cầu theo độ khó
        difficulty_requirements = {
            "easy": """
    **DIFFICULTY: EASY (Band 6-7)**
    - Use common, everyday vocabulary that is easy to understand
    - Simple definitions with clear examples
    - Suitable for IELTS 6.0-7.0 learners
    - Less academic, more conversational
    """,
            "medium": """
    **DIFFICULTY: MEDIUM (Band 7-8)**
    - Use academic vocabulary appropriate for IELTS 7.0-8.0
    - Clear definitions with academic examples
    - Balanced between formal and accessible
    """,
            "advanced": """
    **DIFFICULTY: ADVANCED (Band 8-9)**
    - Use sophisticated academic vocabulary (Band 8.5-9.0)
    - Complex, precise definitions with advanced examples
    - Suitable for learners aiming for Band 8.5-9.0
    """
        }
        
        return f"""
    You are **Professor James Richardson**, a Senior IELTS Examiner with 20+ years of experience at Cambridge English Assessment.

    {difficulty_requirements.get(difficulty, difficulty_requirements['medium'])}

    Provide academic collocations and vocabulary suggestions for:
    Title: "{title}"
    Task Description: "{description}"

    **⚠️ CRITICAL REQUIREMENTS:**
    For EACH vocabulary item, you MUST include:
    1. **word** - The word/phrase itself
    2. **basic_equivalent** - Simple word/phrase it replaces
    3. **meaning_en** - Clear English definition
    4. **meaning_vi** - Vietnamese translation
    5. **example** - IELTS-style example sentence

    **REMEMBER:** Each item MUST have ALL fields.
    Return ONLY raw valid JSON matching this structure:
    [
    {{
        "category": "Topic-Specific Vocabulary",
        "items": [
        {{
            "word": "example word",
            "basic_equivalent": "simple word",
            "meaning_en": "English definition",
            "meaning_vi": "Vietnamese translation",
            "example": "Example sentence"
        }}
        ]
    }}
    ]
    """



# ============================================================================
# Main AI Service
# ============================================================================
class AIService:

    @staticmethod
    def _get_client() -> genai.Client:
        api_key = AIConfig.get_api_key()
        if not api_key:
            raise AIAPIError("GEMINI_API_KEY environment variable is not configured.")
        return genai.Client(api_key=api_key)

    @classmethod
    async def _fetch_image_part(cls, image_url: Optional[str]) -> Optional[types.Part]:
        if not image_url or not image_url.startswith("http"):
            return None
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    if "image" not in content_type:
                        content_type = "image/jpeg"
                    logger.info(f"Loaded reference diagram image for Gemini Multimodal Vision: {image_url}")
                    return types.Part.from_bytes(data=resp.content, mime_type=content_type)
        except Exception as e:
            logger.warning(f"Could not load image for Gemini Vision ({image_url}): {e}")
        return None

    @classmethod
    async def _call_with_retry(
        cls,
        func,
        max_attempts: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        max_attempts = max_attempts or AIConfig.MAX_RETRIES
        timeout = timeout or AIConfig.TIMEOUT
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"AI call attempt {attempt}/{max_attempts} (timeout={timeout}s)")
                return await asyncio.wait_for(func(), timeout=timeout)
            except asyncio.TimeoutError:
                last_error = AIAPIError(f"AI request timed out after {timeout} seconds.")
                logger.warning(f"Attempt {attempt}/{max_attempts} timed out after {timeout}s")
                if attempt < max_attempts:
                    wait_time = 2 ** (attempt - 1)
                    await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    wait_time = 2 ** (attempt - 1)
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_attempts} attempts failed")
                    raise
        raise last_error or AIAPIError("Unknown AI error")

    @classmethod
    async def generate_outline(cls, title: str, task_description: str, difficulty: str = "medium", reference_image_url: Optional[str] = None) -> Any:
        client = cls._get_client()
        prompt = UltimateIELTSPrompt.generate_outline_prompt(title, task_description, difficulty)
        img_part = await cls._fetch_image_part(reference_image_url)
        contents = [img_part, prompt] if img_part else prompt

        async def call_api():
            client = cls._get_client()
            return await client.aio.models.generate_content(
                model=AIConfig.DEFAULT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=AIConfig.OUTLINE_TEMPERATURE
                )
            )

        try:
            response = await cls._call_with_retry(call_api, timeout=AIConfig.OUTLINE_TIMEOUT)
            return GeminiResponseParser.parse_json_response(response.text)
        except AIError:
            raise
        except Exception as err:
            logger.error(f"AIService.generate_outline failed: {err}")
            raise AIAPIError(f"Outline generation failed: {err}")


    @classmethod
    async def generate_collocations(cls, title: str, task_description: str, difficulty: str = "medium", reference_image_url: Optional[str] = None) -> Any:
        prompt = UltimateIELTSPrompt.generate_collocations_prompt(title, task_description, difficulty)
        img_part = await cls._fetch_image_part(reference_image_url)
        contents = [img_part, prompt] if img_part else prompt

        async def call_api():
            client = cls._get_client()
            return await client.aio.models.generate_content(
                model=AIConfig.DEFAULT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=AIConfig.COLLOCATIONS_TEMPERATURE
                )
            )

        try:
            response = await cls._call_with_retry(call_api, timeout=AIConfig.COLLOCATIONS_TIMEOUT)
            logger.info(f"Collocations raw response: {response.text[:200]}")  # Log response
            return GeminiResponseParser.parse_json_response(response.text)
        except AIError:
            raise
        except Exception as err:
            logger.error(f"AIService.generate_collocations failed: {err}")
            raise AIAPIError(f"Collocations generation failed: {err}")

    @classmethod
    async def generate_sample_essay(cls, title: str, task_description: str, references: Optional[dict] = None, difficulty: str = "medium", reference_image_url: Optional[str] = None) -> Any:
        prompt = UltimateIELTSPrompt.generate_sample_essay_prompt(title, task_description, references or {}, difficulty)
        img_part = await cls._fetch_image_part(reference_image_url)
        contents = [img_part, prompt] if img_part else prompt

        async def call_api():
            client = cls._get_client()
            return await client.aio.models.generate_content(
                model=AIConfig.DEFAULT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=AIConfig.SAMPLE_ESSAY_TEMPERATURE
                )
            )

        try:
            response = await cls._call_with_retry(call_api, timeout=AIConfig.SAMPLE_ESSAY_TIMEOUT)
            return GeminiResponseParser.parse_json_response(response.text)
        except AIError:
            raise
        except Exception as err:
            logger.error(f"AIService.generate_sample_essay failed: {err}")
            raise AIAPIError(f"Sample essay generation failed: {err}")

    @classmethod
    async def evaluate_essay(cls, title: str, task_description: str, essay_content: str, reference_image_url: Optional[str] = None) -> Dict[str, Any]:
        prompt = UltimateIELTSPrompt.generate_evaluation_prompt(title, task_description, essay_content)
        img_part = await cls._fetch_image_part(reference_image_url)
        contents = [img_part, prompt] if img_part else prompt

        async def call_api():
            client = cls._get_client()
            return await client.aio.models.generate_content(
                model=AIConfig.DEFAULT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=AIConfig.EVALUATION_TEMPERATURE
                )
            )

        try:
            response = await cls._call_with_retry(call_api, timeout=AIConfig.EVALUATION_TIMEOUT)
            return GeminiResponseParser.parse_json_response(response.text)
        except AIError:
            raise
        except Exception as err:
            logger.error(f"AIService.evaluate_essay failed: {err}")
            raise AIAPIError(f"Essay evaluation failed: {err}")

    @classmethod
    async def generate_improved_sample(cls, essay_content: str) -> Dict[str, Any]:
        """
        Rewrite a student's original essay into an improved Band 9.0 version.

        Args:
            essay_content: Student's original essay text

        Returns:
            Parsed JSON object with improved essay and explanations

        Raises:
            AIAPIError: If API call or timeout fails
            AIResponseParseError: If response JSON parsing fails
        """
        prompt = f"""
        You are **Professor James Richardson**, a Senior IELTS Examiner with 20+ years of experience at Cambridge English Assessment.
        Take the student's original essay below and rewrite an improved Band 9.0 version preserving original ideas:

        Original Essay:
        "{essay_content}"

        Return JSON:
        {{
          "improved_essay": "Improved full Band 9.0 text of essay...",
          "improvements_explanation": ["Upgraded vocabulary to Band 9.0", "Fixed grammatical range"]
        }}
        """

        async def call_api():
            client = cls._get_client()
            return await client.aio.models.generate_content(
                model=AIConfig.DEFAULT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=AIConfig.IMPROVED_SAMPLE_TEMPERATURE
                )
            )

        try:
            response = await cls._call_with_retry(call_api, timeout=AIConfig.IMPROVED_SAMPLE_TIMEOUT)
            return GeminiResponseParser.parse_json_response(response.text)
        except AIError:
            raise
        except Exception as err:
            logger.error(f"AIService.generate_improved_sample failed: {err}")
            raise AIAPIError(f"Improved sample generation failed: {err}")

    @classmethod
    async def answer_question(cls, question: str, prompt_id: str) -> str:
        """Trả lời câu hỏi của user dựa trên đề bài"""
        from .storage_service import StorageService

        try:
            # 1. Lấy prompt document
            prompt_doc = await StorageService.find_prompt_doc(prompt_id)

            # 2. Tạo prompt
            prompt = f"""
            You are an IELTS Writing Assistant. Answer the user's question based on the essay topic below.

            **Topic:** {prompt_doc.title}
            **Task Description:** {prompt_doc.task_description}

            **User's Question:** {question}

            **Rules:**
            - Answer in Vietnamese
            - Be specific, clear, and helpful
            - Keep response concise and STRICTLY under 150-200 words (maximum 200 words).

            Return JSON: {{"answer": "your response here"}}
            """

            async def call_api():
                client = cls._get_client()
                return await client.aio.models.generate_content(
                    model=AIConfig.DEFAULT_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3
                    )
                )

            response = await cls._call_with_retry(call_api)
            try:
                data = GeminiResponseParser.parse_json_response(response.text)
                if isinstance(data, dict) and "answer" in data:
                    return str(data["answer"])
                elif isinstance(data, str):
                    return data
            except Exception:
                if response.text and response.text.strip():
                    return response.text.strip()

            return "Xin lỗi, mình chưa hiểu rõ câu hỏi."
        except Exception as e:
            logger.error(f"Answer question failed: {e}")
            return "Xin lỗi, mình không thể xử lý câu hỏi này. Vui lòng thử lại sau!"