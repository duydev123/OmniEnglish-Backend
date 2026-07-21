from beanie import init_beanie
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os

from models import UserModel
from models.Paragraph import ParagraphModel, SentenceModel, WordModel

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


