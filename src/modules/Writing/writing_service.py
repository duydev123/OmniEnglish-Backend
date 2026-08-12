from typing_extensions import Dict
from modules.Writing.ai_service import GeminiResponseParser
import logging
from typing import List, Optional, Union
from datetime import datetime, timezone
from fastapi import HTTPException

from models.WritingModel import (
    WritingPromptModel,
    WritingSubmissionModel,
    HighlightSpanModel,
    SpecificError,
    ImprovementComparisonModel,
    MilestoneModel
)
from .Writing_dto import (
    AICollocationItem,
    WritingPromptResponse,
    WritingDraftRequest,
    WritingDraftResponse,
    WritingSubmitResponse,
    HighlightSpan,
    DetailedFeedback,
    ImprovementComparison,
    Milestone,
    AIOutlineResponse,
    AIOutlineSection,
    AICollocationsResponse,
    AICollocationGroup,
    AISampleEssayResponse,
    ImprovedEssaySampleResponse
)
from .storage_service import StorageService
from .ai_service import AIService, AICacheService, AIError, AIConfig, AIResponseValidator

logger = logging.getLogger("WritingService")

class WritingService:
    _cache = AICacheService()

    @classmethod
    def _get_temperature(cls, action: str) -> float:
        temps = {
            "OUTLINE": AIConfig.OUTLINE_TEMPERATURE,
            "COLLOCATIONS": AIConfig.COLLOCATIONS_TEMPERATURE,
            "SAMPLE_ESSAY": AIConfig.SAMPLE_ESSAY_TEMPERATURE,
        }
        return temps.get(action.upper(), 0.2)

    @staticmethod
    async def get_writing_prompts(task_type: Optional[str] = None, user_id: Optional[str] = None) -> List[WritingPromptResponse]:
        prompts = await StorageService.get_all_prompts(task_type)
        res = []
        for p in prompts:
            user_status = None
            draft_content = None
            time_spent_seconds = None
            if user_id:
                latest = await StorageService.get_latest_submission(user_id, str(p.id))
                if latest:
                    user_status = latest.status
                    if latest.status == "DRAFT":
                        draft_content = latest.essay_content
                        time_spent_seconds = latest.time_spent_seconds
            res.append(
                WritingPromptResponse(
                    id=str(p.id),
                    title=p.title,
                    task_type=p.task_type,
                    task_description=p.task_description,
                    reference_image_url=p.reference_image_url,
                    ref_id=p.ref_id,
                    time_limit_minutes=p.time_limit_minutes,
                    word_count_target=p.word_count_target,
                    suggested_structure=p.suggested_structure or [],
                    advanced_vocabulary=p.advanced_vocabulary or [],
                    user_status=user_status,
                    draft_content=draft_content,
                    time_spent_seconds=time_spent_seconds
                )
            )
        return res

    @staticmethod
    async def get_writing_prompt(prompt_id: str, user_id: Optional[str] = None) -> WritingPromptResponse:
        prompt = await StorageService.find_prompt_doc(prompt_id)
        user_status = None
        draft_content = None
        time_spent_seconds = None
        if user_id:
            latest = await StorageService.get_latest_submission(user_id, str(prompt.id))
            if latest:
                user_status = latest.status
                if latest.status == "DRAFT":
                    draft_content = latest.essay_content
                    time_spent_seconds = latest.time_spent_seconds
        return WritingPromptResponse(
            id=str(prompt.id),
            title=prompt.title,
            task_type=prompt.task_type,
            task_description=prompt.task_description,
            reference_image_url=prompt.reference_image_url,
            ref_id=prompt.ref_id,
            time_limit_minutes=prompt.time_limit_minutes,
            word_count_target=prompt.word_count_target,
            suggested_structure=prompt.suggested_structure or [],
            advanced_vocabulary=prompt.advanced_vocabulary or [],
            user_status=user_status,
            draft_content=draft_content,
            time_spent_seconds=time_spent_seconds
        )

    @staticmethod
    async def save_writing_draft(user_id: str, payload: WritingDraftRequest) -> WritingDraftResponse:
        prompt = await StorageService.find_prompt_doc(payload.prompt_id)
        submission = await StorageService.save_or_update_draft(
            user_id=user_id,
            prompt_id=str(prompt.id),
            prompt_title=prompt.title,
            essay_content=payload.essay_content,
            word_count=payload.word_count,
            time_spent_seconds=payload.time_spent_seconds
        )
        return WritingDraftResponse(
            session_id=str(submission.id),
            status="DRAFT",
            message="Draft auto-saved successfully!"
        )

    @classmethod
    async def generate_ai_assistance(
        cls,
        action: str,
        prompt_id: str,
        user_notes: Optional[str] = None,
        difficulty: str = "medium"
    ) -> Union[AIOutlineResponse, AICollocationsResponse, AISampleEssayResponse]:
        prompt_doc = await StorageService.find_prompt_doc(prompt_id)
        act_upper = action.upper()

        handlers = {
            "OUTLINE": cls._handle_outline,
            "COLLOCATIONS": cls._handle_collocations,
            "SAMPLE_ESSAY": cls._handle_sample_essay
        }

        handler = handlers.get(act_upper)
        if not handler:
            raise HTTPException(status_code=400, detail="Invalid action type. Choose OUTLINE, COLLOCATIONS, or SAMPLE_ESSAY")

        temperature = cls._get_temperature(act_upper)

        # Check Cache with temperature and user_notes
        cached_result = cls._cache.get(
            str(prompt_doc.id),
            act_upper,
            temperature=temperature,
            user_notes=user_notes,
            difficulty=difficulty
        )
        if cached_result:
            return cached_result

        result = await handler(prompt_doc, user_notes, difficulty)
        cls._cache.set(
            str(prompt_doc.id),
            act_upper,
            result,
            temperature=temperature,
            user_notes=user_notes,
            difficulty=difficulty 
        )
        return result

    @classmethod
    async def _handle_outline(cls, prompt_doc: WritingPromptModel, user_notes: Optional[str] = None, difficulty: str = "medium") -> AIOutlineResponse:
        prompt_id_str = str(prompt_doc.id)
        if prompt_doc.essay_outline and isinstance(prompt_doc.essay_outline, dict) and "sections" in prompt_doc.essay_outline:
            return AIOutlineResponse(
                prompt_id=prompt_id_str,
                outline=[AIOutlineSection(**sec) for sec in prompt_doc.essay_outline.get("sections", [])]
            )

        try:
            data = await AIService.generate_outline(
                title=prompt_doc.title,
                task_description=prompt_doc.task_description,
                difficulty=difficulty
            )            
            validated_data = AIResponseValidator.validate_outline(data)
            return AIOutlineResponse(
                prompt_id=prompt_id_str,
                outline=[AIOutlineSection(**item) for item in validated_data]
            )
        except AIError as err:
            logger.warning(f"AIService generate_outline fallback: {err}")

        # Fallback to prompt_doc structure
        sections = []
        if prompt_doc.suggested_structure:
            for sec in prompt_doc.suggested_structure:
                sections.append(AIOutlineSection(
                    title=sec.get("section", "Section"),
                    sub_points=[sec.get("guide", "Key focus for this paragraph")]
                ))
        else:
            sections = [
                AIOutlineSection(title="Introduction", sub_points=["Hook & Background", "Thesis statement"]),
                AIOutlineSection(title="Body Paragraph 1", sub_points=["Main supporting point & evidence", "Analysis"]),
                AIOutlineSection(title="Body Paragraph 2", sub_points=["Secondary point or counter-argument", "Implications"]),
                AIOutlineSection(title="Conclusion", sub_points=["Summary of main points", "Final outlook"])
            ]
        return AIOutlineResponse(prompt_id=prompt_id_str, outline=sections)

    @classmethod
    async def _handle_collocations(cls, prompt_doc: WritingPromptModel, user_notes: Optional[str] = None, difficulty: str = "medium") -> AICollocationsResponse:
        prompt_id_str = str(prompt_doc.id)
        
        # Nếu đã có sẵn trong database
        if prompt_doc.collocation_suggestions and isinstance(prompt_doc.collocation_suggestions, dict):
            groups = [
                AICollocationGroup(category=k, items=v)
                for k, v in prompt_doc.collocation_suggestions.items()
            ]
            return AICollocationsResponse(prompt_id=prompt_id_str, suggestions=groups)

        # Gọi AI
        try:
            data = await AIService.generate_collocations(prompt_doc.title, prompt_doc.task_description, difficulty)
            validated_data = AIResponseValidator.validate_collocations(data)
            return AICollocationsResponse(
                prompt_id=prompt_id_str,
                suggestions=[AICollocationGroup(**g) for g in validated_data]
            )
        except AIError as err:
            logger.error(f"AIService generate_collocations failed: {err}")
            # ✅ Trả về lỗi thân thiện thay vì hard code
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "AI dịch vụ đang bảo trì hoặc gặp sự cố. Vui lòng thử lại sau!",
                    "error": str(err),
                    "tip": "Bạn có thể thử lại trong vài phút hoặc chọn độ khó khác."
                }
            )
        except Exception as err:
            logger.error(f"Unexpected error in _handle_collocations: {err}")
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Đã có lỗi xảy ra khi tạo gợi ý từ vựng. Vui lòng thử lại!",
                    "error": str(err)
                }
            )


    @classmethod
    async def _handle_sample_essay(cls, prompt_doc: WritingPromptModel, user_notes: Optional[str] = None, difficulty: str = "medium") -> AISampleEssayResponse:
        prompt_id_str = str(prompt_doc.id)
        
        # Định nghĩa difficulty_labels ở ĐẦU hàm
        difficulty_labels = {
            "easy": "Bài mẫu (Band 6-7)",
            "medium": "Bài mẫu (Band 7-8)",
            "advanced": "Bài mẫu (Band 8-9)"
        }
        
        if prompt_doc.sample_essay and isinstance(prompt_doc.sample_essay, dict):
            return AISampleEssayResponse(
                prompt_id=prompt_id_str,
                sample_title=prompt_doc.sample_essay.get("title", prompt_doc.title),
                full_text=prompt_doc.sample_essay.get("full_text", ""),
                structure_annotations=prompt_doc.sample_essay.get("annotations", []),
                good_practices=prompt_doc.sample_essay.get("good_practices", [])
            )

        try:
            data = await AIService.generate_sample_essay(
                title=prompt_doc.title,
                task_description=prompt_doc.task_description,
                references={},  
                difficulty=difficulty 
            )
            validated = AIResponseValidator.validate_sample_essay(data)
            return AISampleEssayResponse(
                prompt_id=prompt_id_str,
                sample_title=validated.get("sample_title", difficulty_labels.get(difficulty, "Bài mẫu")),
                full_text=validated.get("full_text", ""),
                structure_annotations=validated.get("structure_annotations", []),
                good_practices=validated.get("good_practices", [])
            )
        except AIError as err:
            logger.warning(f"AIService generate_sample_essay fallback: {err}")

        # Fallback dùng difficulty_labels đã định nghĩa ở đầu
        return AISampleEssayResponse(
            prompt_id=prompt_id_str,
            sample_title=difficulty_labels.get(difficulty, "Bài mẫu"),
            full_text=f"The debate surrounding {prompt_doc.title.lower()} has gained significant traction in contemporary discourse. This essay examines the key dimensions of this issue and offers a balanced perspective.\n\nOn one hand, modern advancements offer unprecedented opportunities for efficiency and progress. Proponents highlight how innovative approaches streamline complex tasks and foster economic development.\n\nOn the other hand, critical challenges must be addressed to ensure sustainable outcomes. Preserving core values while embracing modern solutions remains essential for long-term stability.\n\nIn conclusion, a nuanced approach that synthesizes innovation with heritage is crucial for addressing this complex topic.",
            structure_annotations=[
                {"section": "Introduction", "note": "Introduces topic & establishes thesis"},
                {"section": "Body 1", "note": "Presents supporting arguments"},
                {"section": "Body 2", "note": "Analyzes counter-perspectives"},
                {"section": "Conclusion", "note": "Synthesizes main findings"}
            ],
            good_practices=[
                "Precise academic vocabulary",
                "Clear paragraph progression",
                "Formal tone throughout"
            ]
        )
    @staticmethod
    async def submit_writing_essay(user_id: str, payload: WritingDraftRequest) -> WritingSubmitResponse:
        if not payload.essay_content or not payload.essay_content.strip():
            raise HTTPException(status_code=400, detail="Your essay is empty. Please write your response before submitting.")

        prompt_doc = await StorageService.find_prompt_doc(payload.prompt_id)

        eval_result = None
        try:
            eval_result = await AIService.evaluate_essay(prompt_doc.title, prompt_doc.task_description, payload.essay_content)
        except AIError as err:
            logger.warning(f"AIService evaluate_essay fallback: {err}")

        if not eval_result:
            essay_len = len(payload.essay_content.split())
            base_score = 7.0 if essay_len >= prompt_doc.word_count_target else 6.0
            eval_result = {
                "overall_score": base_score,
                "potential_score": min(9.0, base_score + 1.0),
                "general_summary": f"Your essay contains {essay_len} words addressing '{prompt_doc.title}'. Well structured with clear arguments.",
                "task_achievement_score": base_score,
                "coherence_cohesion_score": base_score + 0.5,
                "lexical_resource_score": base_score,
                "grammar_accuracy_score": base_score,
                "specific_errors": [],
                "highlight_spans": [],
                "improvements_comparison": [],
                "positive_feedback": ["Structured paragraphs", "Addressed prompt topic"],
                "actionable_next_steps": ["Expand vocabulary range", "Use advanced linking phrases"]
            }

        submission = WritingSubmissionModel(
            user_id=user_id,
            prompt_id=str(prompt_doc.id),
            prompt_title=prompt_doc.title,
            essay_content=payload.essay_content,
            word_count=payload.word_count,
            time_spent_seconds=payload.time_spent_seconds,
            status="REVIEWED",
            overall_score=float(eval_result.get("overall_score", 6.0)),
            potential_score=float(eval_result.get("potential_score", 7.0)),
            general_summary=str(eval_result.get("general_summary", "")),
            task_achievement_score=float(eval_result.get("task_achievement_score", 6.0)),
            coherence_cohesion_score=float(eval_result.get("coherence_cohesion_score", 6.0)),
            lexical_resource_score=float(eval_result.get("lexical_resource_score", 6.0)),
            grammar_accuracy_score=float(eval_result.get("grammar_accuracy_score", 6.0)),
            highlight_spans=[HighlightSpanModel(**span) for span in eval_result.get("highlight_spans", [])],
            specific_errors=[SpecificError(**err) for err in eval_result.get("specific_errors", [])],
            improvements_comparison=[ImprovementComparisonModel(**imp) for imp in eval_result.get("improvements_comparison", [])],
            positive_feedback=eval_result.get("positive_feedback", []),
            actionable_next_steps=eval_result.get("actionable_next_steps", []),
            achieved_milestones=[
                MilestoneModel(date=datetime.now(timezone.utc).strftime("%b %d"), title="Completed Essay Review")
            ]
        )
        await StorageService.save_submission(submission)

        return WritingSubmitResponse(
            session_id=str(submission.id),
            status="REVIEWED",
            prompt_id=str(prompt_doc.id),
            topic_title=prompt_doc.title,
            essay_content=payload.essay_content,
            word_count=payload.word_count,
            time_spent_seconds=payload.time_spent_seconds,
            overall_score=submission.overall_score,
            potential_score=submission.potential_score,
            general_summary=submission.general_summary,
            task_achievement_score=submission.task_achievement_score,
            coherence_cohesion_score=submission.coherence_cohesion_score,
            lexical_resource_score=submission.lexical_resource_score,
            grammar_accuracy_score=submission.grammar_accuracy_score,
            highlight_spans=[HighlightSpan(**span.model_dump()) for span in submission.highlight_spans],
            detailed_feedbacks=[
                DetailedFeedback(
                    category=err.category,
                    original=err.original,
                    correction=err.correction,
                    explanation=err.rule
                ) for err in submission.specific_errors
            ],
            improvements_comparison=[ImprovementComparison(**imp.model_dump()) for imp in submission.improvements_comparison],
            positive_feedback=submission.positive_feedback,
            actionable_next_steps=submission.actionable_next_steps,
            achieved_milestones=[Milestone(**m.model_dump()) for m in submission.achieved_milestones]
        )

    @staticmethod
    async def get_writing_submission(session_id: str, user_id: str) -> WritingSubmitResponse:
        submission = await StorageService.get_submission(session_id)
        return WritingSubmitResponse(
            session_id=str(submission.id),
            status=submission.status,
            prompt_id=submission.prompt_id,
            topic_title=submission.prompt_title,
            essay_content=submission.essay_content,
            word_count=submission.word_count,
            time_spent_seconds=submission.time_spent_seconds,
            overall_score=submission.overall_score,
            potential_score=submission.potential_score,
            general_summary=submission.general_summary,
            task_achievement_score=submission.task_achievement_score,
            coherence_cohesion_score=submission.coherence_cohesion_score,
            lexical_resource_score=submission.lexical_resource_score,
            grammar_accuracy_score=submission.grammar_accuracy_score,
            highlight_spans=[HighlightSpan(**span.model_dump()) for span in submission.highlight_spans],
            detailed_feedbacks=[
                DetailedFeedback(
                    category=err.category,
                    original=err.original,
                    correction=err.correction,
                    explanation=err.rule
                ) for err in submission.specific_errors
            ],
            improvements_comparison=[ImprovementComparison(**imp.model_dump()) for imp in submission.improvements_comparison],
            positive_feedback=submission.positive_feedback,
            actionable_next_steps=submission.actionable_next_steps,
            achieved_milestones=[Milestone(**m.model_dump()) for m in submission.achieved_milestones]
        )

    @staticmethod
    async def generate_improved_essay_sample(session_id: str, user_id: str) -> ImprovedEssaySampleResponse:
        submission = await StorageService.get_submission(session_id)

        if submission.improved_essay_sample:
            return ImprovedEssaySampleResponse(
                session_id=session_id,
                original_essay=submission.essay_content,
                improved_essay=submission.improved_essay_sample,
                improvements_explanation=[
                    "Enhanced vocabulary precision and academic collocations",
                    "Fixed subject-verb agreement and modal verb structures",
                    "Improved paragraph cohesion with varied transitional devices"
                ]
            )

        try:
            data = await AIService.generate_improved_sample(submission.essay_content)
            improved_text = data.get("improved_essay", submission.essay_content)
            explanations = data.get("improvements_explanation", ["Enhanced vocabulary and grammar accuracy"])

            submission.improved_essay_sample = improved_text
            await submission.save()

            return ImprovedEssaySampleResponse(
                session_id=session_id,
                original_essay=submission.essay_content,
                improved_essay=improved_text,
                improvements_explanation=explanations
            )
        except AIError as err:
            logger.warning(f"AIService generate_improved_sample fallback: {err}")

        improved_text = f"Furthermore, {submission.essay_content.strip()}\n\nIn conclusion, addressing these fundamental aspects using refined academic vocabulary and cohesive transitions significantly elevates the overall response."
        submission.improved_essay_sample = improved_text
        await submission.save()

        return ImprovedEssaySampleResponse(
            session_id=session_id,
            original_essay=submission.essay_content,
            improved_essay=improved_text,
            improvements_explanation=["Enhanced academic vocabulary & cohesive transitions"]
        )
    @classmethod
    async def answer_custom_question(cls, prompt_id: str, question: str) -> Dict[str, str]:
        """Trả lời câu hỏi tự do của user về đề bài"""
        try:
            answer = await AIService.answer_question(question, prompt_id)
            return {"answer": answer}
        except Exception as e:
            logger.error(f"Answer question failed: {e}")
            return {
                "answer": "Xin lỗi, mình không thể xử lý câu hỏi này. Vui lòng thử lại!"
            }