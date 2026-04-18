"""Upload route — accepts a video file and stores it locally."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile

from models.schemas import UploadResponse
from services.storage import OutputStore, VideoStore, generate_run_id

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_MIME_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
_MAX_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("/upload", response_model=UploadResponse, summary="Upload a running video")
async def upload_video(file: UploadFile) -> UploadResponse:
    """Accept a video file upload and persist it for later processing.

    The returned ``run_id`` should be used in subsequent calls to
    ``POST /process/{run_id}`` and ``GET /run/{run_id}``.
    """
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. "
                   "Upload an MP4, MOV, AVI, or WebM file.",
        )

    data = await file.read()
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data) / 1024 / 1024:.1f} MB). Maximum is 500 MB.",
        )

    run_id = generate_run_id()
    VideoStore.save(run_id, data)

    # Create a pending status record immediately so GET /run/{id} returns something
    OutputStore.save(run_id, {"run_id": run_id, "status": "pending"})

    logger.info("Uploaded video for run_id=%s (%d bytes)", run_id, len(data))
    return UploadResponse(run_id=run_id, message="Video uploaded. Call POST /process/{run_id} to start analysis.")
