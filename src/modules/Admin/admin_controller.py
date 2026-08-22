from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from .admin_dto import (
    ContentSetDTO,
    CreateContentSetRequest,
    UpdateContentSetRequest,
    AdminCMSStatsDTO,
    AdminUserDTO,
    CreateAdminUserRequest,
    UpdateAdminUserRequest,
)
from .admin_service import AdminService

router = APIRouter()

@router.get("/cms/content-sets", response_model=List[ContentSetDTO])
async def get_cms_content_sets():
    """Fetch real content sets from MongoDB for Admin CMS"""
    return await AdminService.get_cms_content_sets()

@router.post("/cms/content-sets", response_model=ContentSetDTO)
async def create_content_set(payload: CreateContentSetRequest):
    """Create a new content set in MongoDB"""
    return await AdminService.create_content_set(payload)

@router.put("/cms/content-sets/{set_id}", response_model=ContentSetDTO)
async def update_content_set(set_id: str, payload: UpdateContentSetRequest):
    """Update content set title, category, status in MongoDB"""
    try:
        return await AdminService.update_content_set(set_id, payload)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/cms/content-sets/{set_id}")
async def delete_content_set(set_id: str):
    """Delete content set from MongoDB"""
    return await AdminService.delete_content_set(set_id)

@router.get("/cms/stats", response_model=AdminCMSStatsDTO)
async def get_cms_stats():
    """Fetch real CMS item counts and published totals from MongoDB"""
    return await AdminService.get_cms_stats()

# =====================================================================
# USER MANAGEMENT ROUTES
# =====================================================================

@router.get("/users", response_model=List[AdminUserDTO])
async def get_admin_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    proficiency: Optional[str] = None,
):
    """Fetch users from MongoDB for Admin User Management table"""
    return await AdminService.get_users(
        search=search,
        role=role,
        status_filter=status,
        proficiency=proficiency,
    )

@router.post("/users", response_model=AdminUserDTO)
async def create_admin_user(payload: CreateAdminUserRequest):
    """Create a new student or admin user in MongoDB"""
    try:
        return await AdminService.create_user(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}", response_model=AdminUserDTO)
async def update_admin_user(user_id: str, payload: UpdateAdminUserRequest):
    """Update user role, status (Active/Suspended), or proficiency level in MongoDB"""
    try:
        return await AdminService.update_user(user_id, payload)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_admin_user(user_id: str):
    """Delete user from MongoDB"""
    return await AdminService.delete_user(user_id)

@router.get("/settings")
async def get_system_settings():
    """Lấy cấu hình hệ thống (Bảo trì, Prompt AI, Max tokens...)"""
    return {"status": "ok", "maintenance": False}

@router.put("/settings")
async def update_system_settings(payload: dict):
    """Admin cập nhật lại thông số AI cho ứng dụng"""
    return {"status": "updated", "data": payload}