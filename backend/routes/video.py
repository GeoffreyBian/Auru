"""Video route — streams a stored video file with range-request support."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from services.storage import VideoStore

logger = logging.getLogger(__name__)
router = APIRouter()

_CHUNK_SIZE = 1024 * 1024  # 1 MB chunks


def _range_response(path: Path, request: Request) -> StreamingResponse:
    """Return a partial-content response honouring ``Range`` headers."""
    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        try:
            range_value = range_header.strip().replace("bytes=", "")
            start_str, end_str = range_value.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        except (ValueError, AttributeError):
            raise HTTPException(status_code=416, detail="Invalid Range header.")

        if start >= file_size or end >= file_size:
            raise HTTPException(
                status_code=416,
                detail=f"Range {start}-{end} not satisfiable for file of size {file_size}.",
            )

        def _stream():
            with open(path, "rb") as fh:
                fh.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = fh.read(min(_CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            _stream(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
            },
        )

    # No range header — stream the whole file
    def _full_stream():
        with open(path, "rb") as fh:
            while chunk := fh.read(_CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        _full_stream(),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


@router.get("/video/{run_id}", summary="Stream the video for a run")
async def stream_video(run_id: str, request: Request):
    """Stream the raw uploaded video file for *run_id*.

    Supports ``Range`` requests so browser ``<video>`` elements can seek.
    """
    video_path = VideoStore.path(run_id)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"No video found for run_id={run_id!r}.")

    return _range_response(video_path, request)
