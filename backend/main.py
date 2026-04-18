"""Auru FastAPI application entry point.

Start with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import process_router, runs_router, upload_router, video_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Auru API",
    description=(
        "Biomechanical running analysis API. "
        "Upload a running video, trigger analysis, and retrieve metrics and coaching insights."
    ),
    version="1.0.0",
)

# Allow the Next.js dev server (and production origin) to hit the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, tags=["Upload"])
app.include_router(process_router, tags=["Processing"])
app.include_router(runs_router, tags=["Runs"])
app.include_router(video_router, tags=["Video"])


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}
