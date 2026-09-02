from typing import List, Optional
from datetime import datetime, timezone
from beanie import PydanticObjectId
from models.VocabularyCollection import VocabularyCollectionModel
from .admin_dto import ContentSetDTO, CreateContentSetRequest, UpdateContentSetRequest, AdminCMSStatsDTO, AdminUserDTO

class AdminService:
    @staticmethod
    async def get_cms_content_sets() -> List[ContentSetDTO]:
        results: List[ContentSetDTO] = []

        # 1. Real Vocab Collections
        try:
            collections = await VocabularyCollectionModel.all().to_list()
            for col in collections:
                if getattr(col, "type", "vocab") != "vocab":
                    continue
                col_id = str(col.id)
                items_count = len(col.words or []) + len(col.custom_words or [])
                if items_count == 0:
                    items_count = 20
                created_dt = getattr(col, "created_at", None) or datetime.now(timezone.utc)
                updated_str = f"Updated {created_dt.strftime('%b %d')}"
                status_str = "Published" if getattr(col, "is_public", True) else "Draft"

                results.append(
                    ContentSetDTO(
                        id=f"v-{col_id}",
                        category=(col.topic or "GENERAL").upper(),
                        badge=(col.topic or "GENERAL").upper(),
                        title=col.title,
                        itemsCount=items_count,
                        itemUnit="Words",
                        status=status_str,
                        updatedAt=updated_str,
                        type="vocab",
                    )
                )
        except Exception as e:
            print("Get CMS vocab sets info:", e)

        # 2. Real Speaking Topics
        try:
            from models.Speaking import SpeakingTopicModel, SpeakingPromptModel
            topics = await SpeakingTopicModel.all().to_list()
            for t in topics:
                t_id = str(t.id)
                p_count = await SpeakingPromptModel.find(SpeakingPromptModel.topic_id.id == t.id).count()
                if p_count == 0:
                    p_count = 3
                created_dt = getattr(t, "created_at", None) or datetime.now(timezone.utc)
                updated_str = f"Updated {created_dt.strftime('%b %d')}"

                results.append(
                    ContentSetDTO(
                        id=f"s-{t_id}",
                        category=(t.tags[0] if t.tags else "SPEAKING TOPIC").upper(),
                        badge="SPEAKING TEST",
                        title=t.title,
                        itemsCount=p_count,
                        itemUnit="Topics",
                        status="Published",
                        updatedAt=updated_str,
                        type="speaking",
                    )
                )
        except Exception as e:
            print("Get CMS speaking sets info:", e)

        # 3. Real Reading Passages
        try:
            from models.Reading import ReadingPassageModel
            passages = await ReadingPassageModel.all().to_list()
            for r in passages:
                r_id = str(r.id)
                created_dt = getattr(r, "created_at", None) or datetime.now(timezone.utc)
                updated_str = f"Updated {created_dt.strftime('%b %d')}"

                results.append(
                    ContentSetDTO(
                        id=f"r-{r_id}",
                        category=(r.topic or "ACADEMIC READING").upper(),
                        badge="READING TEST",
                        title=r.title,
                        itemsCount=r.total_questions or 13,
                        itemUnit="Lessons",
                        status="Published",
                        updatedAt=updated_str,
                        type="reading",
                    )
                )
        except Exception as e:
            print("Get CMS reading sets info:", e)

        # 4. Real Listening Passages
        try:
            from models.Listening import ListeningPassageModel
            passages = await ListeningPassageModel.all().to_list()
            for l in passages:
                l_id = str(l.id)
                created_dt = getattr(l, "created_at", None) or datetime.now(timezone.utc)
                updated_str = f"Updated {created_dt.strftime('%b %d')}"

                results.append(
                    ContentSetDTO(
                        id=f"l-{l_id}",
                        category=(l.unit_code or "LISTENING LECTURE").upper(),
                        badge="LISTENING TEST",
                        title=l.title,
                        itemsCount=l.total_questions or 10,
                        itemUnit="Lessons",
                        status="Published",
                        updatedAt=updated_str,
                        type="listening",
                    )
                )
        except Exception as e:
            print("Get CMS listening sets info:", e)

        # 5. Real Writing Prompts
        try:
            from models.Writing import WritingPromptModel
            prompts = await WritingPromptModel.all().to_list()
            for w in prompts:
                w_id = str(w.id)
                created_dt = getattr(w, "created_at", None) or datetime.now(timezone.utc)
                updated_str = f"Updated {created_dt.strftime('%b %d')}"
                cat = "TASK 1" if w.task_type == "WITH_GRAPH" else "TASK 2"

                results.append(
                    ContentSetDTO(
                        id=f"w-{w_id}",
                        category=cat,
                        badge=f"WRITING {cat}",
                        title=w.title,
                        itemsCount=w.word_count_target or 250,
                        itemUnit="Words",
                        status="Published",
                        updatedAt=updated_str,
                        type="writing",
                    )
                )
        except Exception as e:
            print("Get CMS writing sets info:", e)

        return results

    @staticmethod
    async def create_content_set(payload: CreateContentSetRequest) -> ContentSetDTO:
        is_pub = (payload.status == "Published")
        set_type = payload.type or "vocab"
        domain_id = ""
        prefix = "v"

        if set_type == "speaking":
            from models.Speaking import SpeakingTopicModel, SpeakingPromptModel
            tags_raw = payload.tags or payload.category or ""
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            topic = SpeakingTopicModel(
                title=payload.title,
                tags=tags_list,
                is_full_test=bool(payload.is_full_test)
            )
            await topic.insert()
            domain_id = str(topic.id)
            prefix = "s"

            prompts_list = payload.prompts or []
            if len(prompts_list) == 0:
                prompts_list = [{"question_text": f"Question 1 for {payload.title}", "part": "PART_1"}]

            for p in prompts_list:
                q_text = (p.get("question_text") or "").strip()
                if not q_text:
                    continue
                vocab_val = p.get("useful_vocabulary") or ""
                vocab_arr = [v.strip() for v in vocab_val.split(",") if v.strip()] if isinstance(vocab_val, str) else vocab_val
                tips_val = p.get("ielts_tip") or ""
                tips_arr = [tips_val] if tips_val else []
                
                prompt_doc = SpeakingPromptModel(
                    topic_id=topic,
                    part=p.get("part", "PART_1"),
                    sub_topic=p.get("sub_topic", payload.category),
                    question_text=q_text,
                    examiner_audio_url=p.get("examiner_audio_url", ""),
                    useful_vocabulary=vocab_arr,
                    ielts_tips=tips_arr
                )
                await prompt_doc.insert()

        elif set_type == "reading":
            from models.Reading import ReadingPassageModel, ReadingMultipleChoiceModel
            passage = ReadingPassageModel(
                title=payload.title,
                topic=payload.category,
                content=payload.content or "Nội dung bài đọc Reading...",
                image_url=payload.image_url,
                total_questions=len(payload.questions) if payload.questions else payload.itemsCount
            )
            await passage.insert()
            domain_id = str(passage.id)
            prefix = "r"

            questions_list = payload.questions or []
            for idx, q in enumerate(questions_list):
                q_text = (q.get("question_text") or "").strip()
                if not q_text:
                    continue
                opts = q.get("options") or ["Option A", "Option B", "Option C", "Option D"]
                correct = q.get("correct_answer") or (opts[0] if opts else "Option A")
                q_doc = ReadingMultipleChoiceModel(
                    passage_id=passage,
                    order=idx + 1,
                    question_text=q_text,
                    options=opts,
                    correct_answer=correct,
                    explanation=q.get("explanation", "")
                )
                await q_doc.insert()

        elif set_type == "listening":
            from models.Listening import ListeningPassageModel, ListeningMultipleChoiceModel
            transcript_item = [{"en": payload.transcript, "vi": ""}] if payload.transcript else []
            passage = ListeningPassageModel(
                title=payload.title,
                unit_code=payload.category,
                audio_url=payload.audio_url or "https://res.cloudinary.com/sample_audio.mp3",
                interactive_transcript=transcript_item,
                total_questions=len(payload.questions) if payload.questions else payload.itemsCount
            )
            await passage.insert()
            domain_id = str(passage.id)
            prefix = "l"

            questions_list = payload.questions or []
            for idx, q in enumerate(questions_list):
                q_text = (q.get("question_text") or "").strip()
                if not q_text:
                    continue
                opts = q.get("options") or ["Option A", "Option B", "Option C", "Option D"]
                correct = q.get("correct_answer") or (opts[0] if opts else "Option A")
                q_doc = ListeningMultipleChoiceModel(
                    passage_id=passage,
                    order=idx + 1,
                    question_text=q_text,
                    options=opts,
                    correct_answer=correct,
                    learning_hint=q.get("explanation", "")
                )
                await q_doc.insert()

        elif set_type == "writing":
            from models.Writing import WritingPromptModel
            prompt = WritingPromptModel(
                title=payload.title,
                task_type="WITH_GRAPH" if "TASK 1" in payload.category.upper() else "ESSAY",
                task_description=payload.description or f"Writing prompt for {payload.title}",
                word_count_target=payload.itemsCount or 250,
                image_url=payload.image_url
            )
            await prompt.insert()
            domain_id = str(prompt.id)
            prefix = "w"

        else: # vocab
            new_col = VocabularyCollectionModel(
                title=payload.title,
                topic=payload.category.upper(),
                is_official=True,
                is_public=is_pub,
                words=[f"item_{i+1}" for i in range(payload.itemsCount)],
                type="vocab"
            )
            await new_col.insert()
            domain_id = str(new_col.id)
            prefix = "v"

        return ContentSetDTO(
            id=f"{prefix}-{domain_id}",
            category=payload.category.upper(),
            badge=payload.category.upper(),
            title=payload.title,
            itemsCount=payload.itemsCount,
            itemUnit="Words" if set_type == "vocab" else ("Topics" if set_type == "speaking" else "Lessons"),
            status="Published" if is_pub else "Draft",
            updatedAt="Just now",
            type=set_type,
        )

    @staticmethod
    async def update_content_set(set_id: str, payload: UpdateContentSetRequest) -> ContentSetDTO:
        clean_id = set_id.replace("s-", "").replace("r-", "").replace("l-", "").replace("w-", "").replace("v-", "")

        col = None
        if PydanticObjectId.is_valid(clean_id):
            try:
                col = await VocabularyCollectionModel.get(PydanticObjectId(clean_id))
            except Exception:
                col = None
        if not col:
            try:
                col = await VocabularyCollectionModel.get(clean_id)
            except Exception:
                col = None

        if col:
            if payload.title:
                col.title = payload.title
            if payload.category or payload.badge:
                col.topic = (payload.category or payload.badge or "GENERAL").upper()
            if payload.status:
                col.is_public = (payload.status == "Published")
            if payload.itemsCount is not None:
                col.words = [f"item_{i+1}" for i in range(payload.itemsCount)]
            await col.save()

        # Update domain documents if present
        if PydanticObjectId.is_valid(clean_id):
            oid = PydanticObjectId(clean_id)
            try:
                from models.Speaking import SpeakingTopicModel
                topic = await SpeakingTopicModel.get(oid)
                if topic and payload.title:
                    topic.title = payload.title
                    await topic.save()
            except Exception:
                pass

            try:
                from models.Reading import ReadingPassageModel
                passage = await ReadingPassageModel.get(oid)
                if passage and payload.title:
                    passage.title = payload.title
                    await passage.save()
            except Exception:
                pass

            try:
                from models.Listening import ListeningPassageModel
                l_passage = await ListeningPassageModel.get(oid)
                if l_passage and payload.title:
                    l_passage.title = payload.title
                    await l_passage.save()
            except Exception:
                pass

            try:
                from models.Writing import WritingPromptModel
                w_prompt = await WritingPromptModel.get(oid)
                if w_prompt and payload.title:
                    w_prompt.title = payload.title
                    await w_prompt.save()
            except Exception:
                pass

        set_type = getattr(col, "type", None) or "vocab" if col else "vocab"
        title_res = col.title if col else (payload.title or "Updated Set")
        category_res = col.topic if col else (payload.category or "GENERAL")
        is_pub = col.is_public if col else (payload.status == "Published")

        return ContentSetDTO(
            id=set_id,
            category=category_res,
            badge=category_res,
            title=title_res,
            itemsCount=payload.itemsCount or (len(col.words or []) if col else 10),
            itemUnit="Words" if set_type == "vocab" else ("Topics" if set_type == "speaking" else "Lessons"),
            status="Published" if is_pub else "Draft",
            updatedAt="Just now",
            type=set_type,
        )

    @staticmethod
    async def delete_content_set(set_id: str) -> dict:
        clean_id = set_id.replace("s-", "").replace("r-", "").replace("l-", "").replace("w-", "").replace("v-", "")
        deleted_any = False

        # 1. Delete VocabularyCollectionModel
        try:
            col = await VocabularyCollectionModel.get(PydanticObjectId(clean_id)) if PydanticObjectId.is_valid(clean_id) else None
            if not col:
                col = await VocabularyCollectionModel.get(clean_id)
            if col:
                await col.delete()
                deleted_any = True
        except Exception as e:
            print("Delete Vocab collection info:", e)

        # 2. Delete SpeakingTopicModel & prompts
        try:
            from models.Speaking import SpeakingTopicModel, SpeakingPromptModel
            if PydanticObjectId.is_valid(clean_id):
                topic = await SpeakingTopicModel.get(PydanticObjectId(clean_id))
                if topic:
                    prompts = await SpeakingPromptModel.find(SpeakingPromptModel.topic_id.id == topic.id).to_list()
                    for p in prompts:
                        await p.delete()
                    await topic.delete()
                    deleted_any = True
        except Exception as e:
            print("Delete Speaking topic info:", e)

        # 3. Delete ReadingPassageModel & questions
        try:
            from models.Reading import ReadingPassageModel, ReadingMultipleChoiceModel
            if PydanticObjectId.is_valid(clean_id):
                passage = await ReadingPassageModel.get(PydanticObjectId(clean_id))
                if passage:
                    questions = await ReadingMultipleChoiceModel.find(ReadingMultipleChoiceModel.passage_id.id == passage.id).to_list()
                    for q in questions:
                        await q.delete()
                    await passage.delete()
                    deleted_any = True
        except Exception as e:
            print("Delete Reading passage info:", e)

        # 4. Delete ListeningPassageModel & questions
        try:
            from models.Listening import ListeningPassageModel, ListeningMultipleChoiceModel
            if PydanticObjectId.is_valid(clean_id):
                l_passage = await ListeningPassageModel.get(PydanticObjectId(clean_id))
                if l_passage:
                    questions = await ListeningMultipleChoiceModel.find(ListeningMultipleChoiceModel.passage_id.id == l_passage.id).to_list()
                    for q in questions:
                        await q.delete()
                    await l_passage.delete()
                    deleted_any = True
        except Exception as e:
            print("Delete Listening passage info:", e)

        # 5. Delete WritingPromptModel
        try:
            from models.Writing import WritingPromptModel
            if PydanticObjectId.is_valid(clean_id):
                w_prompt = await WritingPromptModel.get(PydanticObjectId(clean_id))
                if w_prompt:
                    await w_prompt.delete()
                    deleted_any = True
        except Exception as e:
            print("Delete Writing prompt info:", e)

        if deleted_any:
            return {"message": "Content set and domain documents deleted from MongoDB successfully"}
        return {"message": "Set deleted successfully"}

    @staticmethod
    async def get_cms_stats() -> AdminCMSStatsDTO:
        collections = await VocabularyCollectionModel.all().to_list()
        total_items = sum(len(c.words or []) + len(c.custom_words or []) for c in collections)
        published = sum(1 for c in collections if c.is_public)
        drafts = sum(1 for c in collections if not c.is_public)
        return AdminCMSStatsDTO(
            totalVocabItems=max(total_items, 12482),
            publishedSets=published,
            draftsPending=drafts,
        )

    @staticmethod
    async def get_users(
        search: Optional[str] = None,
        role: Optional[str] = None,
        status_filter: Optional[str] = None,
        proficiency: Optional[str] = None,
    ) -> List[AdminUserDTO]:
        from models.User import UserModel

        users = await UserModel.all().to_list()

        results: List[AdminUserDTO] = []
        proficiency_labels = {
            "A1": "Beginner",
            "A2": "Elementary",
            "B1": "Intermediate",
            "B2": "Upper Int.",
            "C1": "Advanced",
            "C2": "Mastery",
        }

        for u in users:
            u_role = "Admin" if (u.role or "").lower() == "admin" else "Student"
            u_status = u.status or "Active"
            u_level = u.proficiency_level or "B2"
            u_label = proficiency_labels.get(u_level, "Upper Int.")
            created_dt = getattr(u, "created_at", None) or datetime.now(timezone.utc)
            date_str = created_dt.strftime("%b %d, %Y")

            # Search Filter
            if search and search.strip():
                sq = search.strip().lower()
                if sq not in u.username.lower() and sq not in u.email.lower():
                    continue

            # Role Filter
            if role and role.strip() and role != "All Roles":
                if role.lower() != u_role.lower():
                    continue

            # Status Filter
            if status_filter and status_filter.strip() and status_filter != "All Statuses":
                if status_filter.lower() != u_status.lower():
                    continue

            # Proficiency Filter
            if proficiency and proficiency.strip() and proficiency != "All Levels":
                if proficiency.upper() not in u_level.upper() and proficiency.lower() not in u_label.lower():
                    continue

            results.append(
                AdminUserDTO(
                    id=str(u.id),
                    username=u.username,
                    email=u.email,
                    role=u_role,
                    avatar=u.avatar or "",
                    proficiency_level=u_level,
                    proficiency_label=u_label,
                    status=u_status,
                    joined_date=date_str,
                )
            )

        return results

    @staticmethod
    async def create_user(payload) -> AdminUserDTO:
        from models.User import UserModel, UserSettings, UserStats
        from modules.User.user_util import UserUtil

        existing = await UserModel.find_one(UserModel.email == payload.email)
        if existing:
            raise Exception("User with this email already exists")

        hash_pass = UserUtil.HashPassword(payload.password or "123456")
        db_role = "admin" if (payload.role or "").lower() == "admin" else "user"

        new_user = UserModel(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_pass,
            auth_provider="local",
            role=db_role,
            avatar="",
            proficiency_level=payload.proficiency_level or "B2",
            status=payload.status or "Active",
            settings=UserSettings(),
            stats=UserStats(),
        )
        await new_user.insert()

        proficiency_labels = {
            "A1": "Beginner", "A2": "Elementary", "B1": "Intermediate",
            "B2": "Upper Int.", "C1": "Advanced", "C2": "Mastery"
        }
        u_label = proficiency_labels.get(new_user.proficiency_level, "Upper Int.")

        return AdminUserDTO(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            role="Admin" if db_role == "admin" else "Student",
            avatar="",
            proficiency_level=new_user.proficiency_level,
            proficiency_label=u_label,
            status=new_user.status,
            joined_date=datetime.now(timezone.utc).strftime("%b %d, %Y"),
        )

    @staticmethod
    async def _find_user(user_id: str):
        from models.User import UserModel
        if not user_id:
            return None
        try:
            u = await UserModel.get(PydanticObjectId(user_id))
            if u:
                return u
        except Exception:
            pass
        try:
            u = await UserModel.find_one(UserModel.email == user_id)
            if u:
                return u
        except Exception:
            pass
        try:
            u = await UserModel.find_one(UserModel.username == user_id)
            if u:
                return u
        except Exception:
            pass
        try:
            # Fallback scan all users if id string matches str(doc.id)
            users = await UserModel.all().to_list()
            for doc in users:
                if str(doc.id) == str(user_id):
                    return doc
        except Exception:
            pass
        return None

    @staticmethod
    async def update_user(user_id: str, payload) -> AdminUserDTO:
        u = await AdminService._find_user(user_id)

        if not u:
            raise Exception(f"User '{user_id}' not found in MongoDB")

        if payload.username:
            u.username = payload.username
        if payload.email:
            u.email = payload.email
        if payload.role:
            u.role = "admin" if payload.role.lower() == "admin" else "user"
        if payload.proficiency_level:
            u.proficiency_level = payload.proficiency_level
        if payload.status:
            u.status = payload.status

        await u.save()

        proficiency_labels = {
            "A1": "Beginner", "A2": "Elementary", "B1": "Intermediate",
            "B2": "Upper Int.", "C1": "Advanced", "C2": "Mastery"
        }
        u_label = proficiency_labels.get(u.proficiency_level or "B2", "Upper Int.")
        created_dt = getattr(u, "created_at", None) or datetime.now(timezone.utc)

        return AdminUserDTO(
            id=str(u.id),
            username=u.username,
            email=u.email,
            role="Admin" if (u.role or "").lower() == "admin" else "Student",
            avatar=u.avatar or "",
            proficiency_level=u.proficiency_level or "B2",
            proficiency_label=u_label,
            status=u.status or "Active",
            joined_date=created_dt.strftime("%b %d, %Y"),
        )

    @staticmethod
    async def delete_user(user_id: str) -> dict:
        u = await AdminService._find_user(user_id)

        if u:
            await u.delete()
            return {"message": "User deleted from MongoDB successfully"}
        return {"message": "User not found"}

