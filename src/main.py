import os
from contextlib import asynccontextmanager

from beanie import init_beanie
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

# Load biến môi trường
load_dotenv()

# Import models
# from models.Paragraph import ParagraphModel, SentenceModel, WordModel
from models.UserModel import UserModel

# Import router
from modules.User import user_controller
from core.exception import setup_exception_handlers
from modules.Listening import listening_controller
from modules.Reading import reading_controller
from modules.Admin import admin_controller
from modules.Grammar import grammar_controller
from modules.Writing import writing_controller
from modules.Speaking import speaking_controller
from modules.Vocabulary import vocab_controller
from modules.Auth import auth_controller
from modules.Seed import seed_controller

from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel,
    UserReadingSessionModel
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_uri = os.getenv("MONGO_URI")
    client = AsyncIOMotorClient(mongo_uri)

    await init_beanie(
        database=client.get_database("omni_english_db"),
        document_models=[ UserModel, ReadingPassageModel,
            ReadingMultipleChoiceModel,
            ReadingHeadingMatchingModel,
            ReadingFillBlankModel,
            ReadingTrueFalseNotGivenModel,
            UserReadingSessionModel,],
    )
    yield
    client.close()


# Config app FastAPI
app = FastAPI(title="omni english web", lifespan=lifespan)

# Config CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
setup_exception_handlers(app)
# Include router

app.include_router(auth_controller.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user_controller.router, prefix="/api/v1/users", tags=["User Profile & Stats"])
app.include_router(admin_controller.router, prefix="/api/v1/admin", tags=["Admin System"])


app.include_router(reading_controller.router, prefix="/api/v1/reading", tags=["Reading Module"])
app.include_router(listening_controller.router, prefix="/api/v1/listening", tags=["Listening Module"])
app.include_router(speaking_controller.router, prefix="/api/v1/speaking", tags=["Speaking Module"])
app.include_router(writing_controller.router, prefix="/api/v1/writing", tags=["Writing Module"])
app.include_router(grammar_controller.router, prefix="/api/v1/grammar", tags=["Grammar Module"])
app.include_router(vocab_controller.router, prefix="/api/v1/vocabulary", tags=["Vocabulary Module"])
app.include_router(seed_controller.router, prefix="/api/v1/seed", tags=["Seed Data"])
@app.get("/")
def read_root():
    return {"message": "Khởi tạo server thành công!"}


