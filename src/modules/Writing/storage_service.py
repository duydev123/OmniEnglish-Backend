import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from beanie import PydanticObjectId

from models.Writing import WritingPromptModel, WritingSubmissionModel

logger = logging.getLogger("StorageService")

class StorageService:

    @staticmethod
    async def find_prompt_doc(prompt_id: str) -> WritingPromptModel:
        prompt_doc = None
        if PydanticObjectId.is_valid(prompt_id):
            prompt_doc = await WritingPromptModel.get(PydanticObjectId(prompt_id))
        
        if not prompt_doc:
            prompt_doc = await WritingPromptModel.find_one(WritingPromptModel.ref_id == prompt_id)
        
        if not prompt_doc:
            prompt_doc = await WritingPromptModel.find_one()

        if not prompt_doc:
            raise HTTPException(status_code=404, detail="Writing prompt not found")
        
        return prompt_doc

    @staticmethod
    async def get_all_prompts(task_type: Optional[str] = None) -> List[WritingPromptModel]:
        if task_type and task_type.upper() in ["WITH_GRAPH", "WITHOUT_GRAPH"]:
            return await WritingPromptModel.find(WritingPromptModel.task_type == task_type.upper()).to_list()
        return await WritingPromptModel.find_all().to_list()

    @staticmethod
    async def save_or_update_draft(
        user_id: str,
        prompt_id: str,
        prompt_title: str,
        essay_content: str,
        word_count: int,
        time_spent_seconds: int
    ) -> WritingSubmissionModel:
        submission = await WritingSubmissionModel.find_one(
            WritingSubmissionModel.user_id == user_id,
            WritingSubmissionModel.prompt_id == prompt_id,
            WritingSubmissionModel.status == "DRAFT"
        )

        if submission:
            submission.essay_content = essay_content
            submission.word_count = word_count
            submission.time_spent_seconds = time_spent_seconds
            submission.updated_at = datetime.now(timezone.utc)
            await submission.save()
        else:
            submission = WritingSubmissionModel(
                user_id=user_id,
                prompt_id=prompt_id,
                prompt_title=prompt_title,
                essay_content=essay_content,
                word_count=word_count,
                time_spent_seconds=time_spent_seconds,
                status="DRAFT"
            )
            await submission.insert()

        return submission

    @staticmethod
    async def save_submission(submission: WritingSubmissionModel) -> WritingSubmissionModel:
        await submission.insert()
        return submission

    @staticmethod
    async def get_submission(session_id: str) -> WritingSubmissionModel:
        if not PydanticObjectId.is_valid(session_id):
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        submission = await WritingSubmissionModel.get(PydanticObjectId(session_id))
        if not submission:
            raise HTTPException(status_code=404, detail="Writing submission session not found")

        return submission

    @staticmethod
    async def get_latest_submission(user_id: str, prompt_id: str) -> Optional[WritingSubmissionModel]:
        try:
            res = WritingSubmissionModel.find(
                WritingSubmissionModel.user_id == user_id,
                WritingSubmissionModel.prompt_id == prompt_id
            ).sort(-WritingSubmissionModel.updated_at).to_list()
            if hasattr(res, "__await__"):
                res = await res
            return res[0] if res and isinstance(res, list) else None
        except Exception:
            return None

    @staticmethod
    async def get_user_highest_score(user_id: str, prompt_id: str) -> Optional[float]:
        try:
            res = WritingSubmissionModel.find(
                WritingSubmissionModel.user_id == user_id,
                WritingSubmissionModel.prompt_id == prompt_id,
                WritingSubmissionModel.status == "REVIEWED"
            ).to_list()
            if hasattr(res, "__await__"):
                res = await res
            scores = [s.overall_score for s in (res or []) if getattr(s, 'overall_score', 0) > 0]
            return max(scores) if scores else None
        except Exception:
            return None

    @staticmethod
    async def get_all_user_submissions(user_id: str) -> List[WritingSubmissionModel]:
        try:
            res = WritingSubmissionModel.find(
                WritingSubmissionModel.user_id == user_id
            ).sort(-WritingSubmissionModel.updated_at).to_list()
            if hasattr(res, "__await__"):
                res = await res
            return res if isinstance(res, list) else []
        except Exception:
            return []
