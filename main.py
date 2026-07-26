from beanie import init_beanie
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os

from models import UserModel
from models.Paragraph import ParagraphModel, SentenceModel, WordModel
from dotenv import load_dotenv

from routes import admin_router, auth_router, grammar_router, listening_router, reading_router, speaking_router, users_router, vocab_router, writing_router

load_dotenv()

app = FastAPI()





@asynccontextmanager
async def lifespan(app: FastAPI):
  MONGO_URI = os.getenv("MONGO_URI")
  client = AsyncIOMotorClient(MONGO_URI)

  await init_beanie(
    database=client["omni_english_db"], 
    document_models=[WordModel, ParagraphModel, SentenceModel, UserModel]
)

@app.get("/")
def Read_Root():
  return "Server is runing..."




app.add_middleware(
  CORSMiddleware,
)


app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["User Profile & Stats"])
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["Admin System"])


app.include_router(reading_router.router, prefix="/api/v1/reading", tags=["Reading Module"])
app.include_router(listening_router.router, prefix="/api/v1/listening", tags=["Listening Module"])
app.include_router(speaking_router.router, prefix="/api/v1/speaking", tags=["Speaking Module"])
app.include_router(writing_router.router, prefix="/api/v1/writing", tags=["Writing Module"])
app.include_router(grammar_router.router, prefix="/api/v1/grammar", tags=["Grammar Module"])
app.include_router(vocab_router.router, prefix="/api/v1/vocabulary", tags=["Vocabulary Module"])