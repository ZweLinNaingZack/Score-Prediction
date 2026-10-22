from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Score Prediction API", lifespan=lifespan)
def parse_origins(raw: str) -> list[str]:
    """`https://site.vercel.app/` and `"https://site.vercel.app"` both mean https://site.vercel.app."""
    found = [o.strip().strip("'\"").rstrip("/") for o in raw.replace("\n", ",").split(",")]
    return [o for o in found if o] or ["*"]


origins = parse_origins(settings.cors_origins)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
