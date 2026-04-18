"""Process route — triggers the analysis pipeline for an uploaded video."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, HTTPException

from models.schemas import ProcessRequest, ProcessResponse, RunStatus
from services.pipeline import run_pipeline
from services.storage import OutputStore, VideoStore

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for running the CPU-bound CV pipeline without blocking the event loop
_executor = ThreadPoolExecutor(max_workers=2)


def _run_pipeline_sync(run_id: str, runner_height_m: float) -> None:
    """Synchronous wrapper called inside the thread pool."""
    try:
        run_pipeline(run_id, runner_height_m)
    except Exception:
        # Errors are persisted by the pipeline itself; just log here.
        logger.exception("Background pipeline failed for run_id=%s", run_id)


@router.post(
    "/process/{run_id}",
    response_model=ProcessResponse,
    summary="Start biomechanical analysis for an uploaded run",
)
async def process_run(
    run_id: str,
    body: ProcessRequest = None,
    background_tasks: BackgroundTasks = None,
) -> ProcessResponse:
    """Trigger the CV analysis pipeline for *run_id*.

    Processing runs in a background thread so the response is returned
    immediately.  Poll ``GET /run/{run_id}`` to check status and retrieve
    results once ``status == "completed"``.
    """
    if body is None:
        body = ProcessRequest()

    if not VideoStore.exists(run_id):
        raise HTTPException(status_code=404, detail=f"No video found for run_id={run_id!r}.")

    existing = OutputStore.load(run_id)
    if existing and existing.get("status") == "processing":
        raise HTTPException(status_code=409, detail="This run is already being processed.")

    # Mark as processing immediately
    OutputStore.update_status(run_id, "processing")

    # Offload the CPU-heavy pipeline to a thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_pipeline_sync,
        run_id,
        body.runner_height_m,
    )

    return ProcessResponse(run_id=run_id, status=RunStatus.processing)
