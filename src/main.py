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
from models.Paragraph import ParagraphModel, SentenceModel, WordModel
from models.UserModel import UserModel

# Import router
from modules.User.user_controller import routerUser
from core.exception import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_uri = os.getenv("MONGO_URI")
    client = AsyncIOMotorClient(mongo_uri)

    await init_beanie(
        database=client.get_database("omni_english_db"),
        document_models=[WordModel, ParagraphModel, SentenceModel, UserModel],
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

app.include_router(routerUser)


@app.get("/")
def read_root():
    return {"message": "Khởi tạo server thành công!"}


