"""Runs route — retrieve analysis results for a completed run."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import RunResult, RunStatus
from services.storage import OutputStore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/run/{run_id}",
    response_model=RunResult,
    summary="Get analysis results for a run",
)
async def get_run(run_id: str) -> RunResult:
    """Return the current status and (if complete) full analysis results for *run_id*.

    Clients should poll this endpoint until ``status`` is ``"completed"`` or
    ``"failed"``.
    """
    data = OutputStore.load(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found.")

    # Normalise status
    status_str = data.get("status", "pending")
    try:
        status = RunStatus(status_str)
    except ValueError:
        status = RunStatus.pending

    if status not in (RunStatus.completed, RunStatus.failed):
        return RunResult(run_id=run_id, status=status)

    if status == RunStatus.failed:
        return RunResult(run_id=run_id, status=status, error=data.get("error"))

    # Build full response from stored data
    from models.schemas import Event, MetricsSummary, TimeSeriesPoint

    raw_metrics = data.get("metrics", {})
    events = [
        Event(
            type=e["type"],
            frame=e["frame"],
            time_sec=e["time_sec"],
        )
        for e in raw_metrics.get("events", [])
    ]

    metrics = MetricsSummary(
        cadence=raw_metrics.get("cadence", 0),
        stride_length=raw_metrics.get("stride_length", 0),
        vertical_oscillation=raw_metrics.get("vertical_oscillation", 0),
        symmetry_score=raw_metrics.get("symmetry_score", 1.0),
        fatigue_frame=raw_metrics.get("fatigue_frame"),
        fatigue_time_sec=raw_metrics.get("fatigue_time_sec"),
        overstriding_count=raw_metrics.get("overstriding_count", 0),
        events=events,
    )

    def _ts(raw: list[dict]) -> list[TimeSeriesPoint]:
        return [TimeSeriesPoint(**p) for p in raw]

    return RunResult(
        run_id=run_id,
        status=status,
        metadata=data.get("metadata", {}),
        metrics=metrics,
        insights=data.get("insights", []),
        cadence_over_time=_ts(data.get("cadence_over_time", [])),
        hip_y_over_time=_ts(data.get("hip_y_over_time", [])),
        left_ankle_y_over_time=_ts(data.get("left_ankle_y_over_time", [])),
        right_ankle_y_over_time=_ts(data.get("right_ankle_y_over_time", [])),
        annotated_video_ready=data.get("annotated_video_ready", False),
    )
