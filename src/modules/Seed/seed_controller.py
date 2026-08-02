from fastapi import APIRouter, status
from .seed_service import SeedService


router = APIRouter()
seed_service = SeedService ()

@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed():
    return await seed_service.seed_reading_only()