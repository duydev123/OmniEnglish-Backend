from typing import List, Optional
from datetime import datetime, timezone
from beanie import PydanticObjectId
from models.VocabularyCollectionModel import VocabularyCollectionModel
from .admin_dto import ContentSetDTO, CreateContentSetRequest, UpdateContentSetRequest, AdminCMSStatsDTO, AdminUserDTO

class AdminService:
    @staticmethod
    async def get_cms_content_sets() -> List[ContentSetDTO]:
        collections = await VocabularyCollectionModel.all().to_list()

        results: List[ContentSetDTO] = []
        for col in collections:
            col_id = str(col.id)
            items_count = len(col.words or []) + len(col.custom_words or [])
            if items_count == 0:
                items_count = 20
            
            created_dt = getattr(col, "created_at", None) or datetime.now(timezone.utc)
            updated_str = f"Updated {created_dt.strftime('%b %d')}"
            
            status_str = "Published" if col.is_public else "Draft"
            
            results.append(
                ContentSetDTO(
                    id=col_id,
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
        return results

    @staticmethod
    async def create_content_set(payload: CreateContentSetRequest) -> ContentSetDTO:
        is_pub = (payload.status == "Published")
        new_col = VocabularyCollectionModel(
            title=payload.title,
            topic=payload.category.upper(),
            is_official=True,
            is_public=is_pub,
            words=[f"word_{i+1}" for i in range(payload.itemsCount)]
        )
        await new_col.insert()
        return ContentSetDTO(
            id=str(new_col.id),
            category=new_col.topic,
            badge=new_col.topic,
            title=new_col.title,
            itemsCount=payload.itemsCount,
            itemUnit="Words",
            status="Published" if is_pub else "Draft",
            updatedAt="Just now",
            type=payload.type or "vocab",
        )

    @staticmethod
    async def update_content_set(set_id: str, payload: UpdateContentSetRequest) -> ContentSetDTO:
        col = None
        try:
            col = await VocabularyCollectionModel.get(PydanticObjectId(set_id))
        except Exception:
            col = None
        
        if not col:
            try:
                col = await VocabularyCollectionModel.get(set_id)
            except Exception:
                col = None

        if not col:
            raise Exception(f"Content set {set_id} not found in MongoDB")

        if payload.title:
            col.title = payload.title
        if payload.category or payload.badge:
            col.topic = (payload.category or payload.badge or "GENERAL").upper()
        if payload.status:
            col.is_public = (payload.status == "Published")
        if payload.itemsCount is not None:
            col.words = [f"word_{i+1}" for i in range(payload.itemsCount)]

        await col.save()

        items_count = len(col.words or [])
        return ContentSetDTO(
            id=str(col.id),
            category=col.topic,
            badge=col.topic,
            title=col.title,
            itemsCount=items_count,
            itemUnit="Words",
            status="Published" if col.is_public else "Draft",
            updatedAt="Just now",
            type="vocab",
        )

    @staticmethod
    async def delete_content_set(set_id: str) -> dict:
        col = None
        try:
            col = await VocabularyCollectionModel.get(PydanticObjectId(set_id))
        except Exception:
            col = None
        
        if not col:
            try:
                col = await VocabularyCollectionModel.get(set_id)
            except Exception:
                col = None

        if col:
            await col.delete()
            return {"message": "Content set deleted from MongoDB successfully"}
        return {"message": "Set not found"}

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
        from models.UserModel import UserModel

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
        from models.UserModel import UserModel, UserSettings, UserStats
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
    async def update_user(user_id: str, payload) -> AdminUserDTO:
        from models.UserModel import UserModel

        u = None
        try:
            u = await UserModel.get(PydanticObjectId(user_id))
        except Exception:
            u = None

        if not u:
            try:
                u = await UserModel.get(user_id)
            except Exception:
                u = None

        if not u:
            raise Exception(f"User {user_id} not found in MongoDB")

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
        from models.UserModel import UserModel

        u = None
        try:
            u = await UserModel.get(PydanticObjectId(user_id))
        except Exception:
            u = None

        if not u:
            try:
                u = await UserModel.get(user_id)
            except Exception:
                u = None

        if u:
            await u.delete()
            return {"message": "User deleted from MongoDB successfully"}
        return {"message": "User not found"}

