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

# Separate pools: analysis is heavier (MediaPipe), annotation is I/O + draw
_analysis_executor  = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis")
_annotate_executor  = ThreadPoolExecutor(max_workers=2, thread_name_prefix="annotate")


def _run_pipeline_sync(run_id: str, runner_height_m: float) -> None:
    try:
        run_pipeline(run_id, runner_height_m)
    except Exception:
        logger.exception("Pipeline failed for run_id=%s", run_id)


def _run_annotation_sync(run_id: str) -> None:
    try:
        from services.annotate import generate_annotated_video
        generate_annotated_video(run_id)
        data = OutputStore.load(run_id)
        if data:
            data["annotated_video_ready"] = True
            OutputStore.save(run_id, data)
        logger.info("Annotation completed for run_id=%s", run_id)
    except Exception:
        logger.exception("Annotation failed for run_id=%s (non-critical)", run_id)


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

    Runs in two sequential background stages:
    1. Pose extraction + metrics (results visible via GET /run/{id} immediately after)
    2. Annotated video generation (annotated_video_ready flips to true when done)

    Poll ``GET /run/{run_id}`` until ``status == "completed"``.
    """
    if body is None:
        body = ProcessRequest()

    if not VideoStore.exists(run_id):
        raise HTTPException(status_code=404, detail=f"No video found for run_id={run_id!r}.")

    existing = OutputStore.load(run_id)
    if existing and existing.get("status") == "processing":
        raise HTTPException(status_code=409, detail="This run is already being processed.")

    OutputStore.update_status(run_id, "processing")

    loop = asyncio.get_event_loop()

    async def _run_both() -> None:
        # Stage 1 — analysis: metrics visible to client as soon as this finishes
        await loop.run_in_executor(_analysis_executor, _run_pipeline_sync, run_id, body.runner_height_m)
        # Stage 2 — annotation: runs independently; client sees annotated_video_ready flip
        data = OutputStore.load(run_id)
        if data and data.get("status") == "completed":
            await loop.run_in_executor(_annotate_executor, _run_annotation_sync, run_id)

    asyncio.create_task(_run_both())

    return ProcessResponse(run_id=run_id, status=RunStatus.processing)
