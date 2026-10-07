"""The app: serve the domain's extraction API."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # this app's .env

import docextract.cache_sqlmodel  # noqa: E402,F401 — register the engine tables
import docextract.corrections_sqlmodel  # noqa: E402,F401
from domain.wire import create_router  # noqa: E402


def _engine():
    from sqlmodel import create_engine

    return create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/app"))


app = FastAPI()
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_router(_engine()))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
