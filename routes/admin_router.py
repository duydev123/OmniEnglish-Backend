from fastapi import APIRouter
# Import schemas (tự định nghĩa thêm)
# from schemas.admin import SystemSettingsResponse, SystemSettingsUpdateRequest

router = APIRouter()

@router.get("/settings")
async def get_system_settings():
    """Lấy cấu hình hệ thống (Bảo trì, Prompt AI, Max tokens...)"""
    pass

@router.put("/settings")
async def update_system_settings(payload: dict):
    """Admin cập nhật lại thông số AI cho ứng dụng"""
    pass