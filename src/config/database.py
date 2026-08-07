# config/database.py

import motor.motor_asyncio
from beanie import init_beanie
from typing import List
from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)
from models.Listening import (
    ListeningPassageModel,
    ListeningAudioSegmentModel,
    ListeningMultipleChoiceModel,
    ListeningCompletionModel,
    UserListeningSessionModel
)

# MongoDB connection string
MONGODB_URI = "mongodb+srv://omni_english_db:duy123@cluster0.0clx1qx.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "omni_english"  # Tên database của bạn

# Khởi tạo client
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)

# Chọn database
database = client[DATABASE_NAME]

async def init_db():
    """Khởi tạo database và các models"""
    # Danh sách tất cả models cần được Beanie quản lý
    models = [
        # Reading models
        ReadingPassageModel,
        ReadingMultipleChoiceModel,
        ReadingHeadingMatchingModel,
        ReadingFillBlankModel,
        ReadingTrueFalseNotGivenModel,
        UserReadingSessionModel,
        
        # Listening models
        ListeningPassageModel,
        ListeningAudioSegmentModel,
        ListeningMultipleChoiceModel,
        ListeningCompletionModel,
        UserListeningSessionModel,
    ]
    
    # Khởi tạo Beanie với database và models
    await init_beanie(
        database=database,
        document_models=models
    )
    
    print("Database connected successfully!")
    print(f"Database: {DATABASE_NAME}")
    
    # Kiểm tra kết nối bằng cách đếm collections
    collections = await database.list_collection_names()
    print(f"Collections: {collections}")

async def close_db():
    """Đóng kết nối database"""
    client.close()
    print("❌ Database connection closed")