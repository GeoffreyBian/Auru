"""Pydantic schemas for request/response models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UploadResponse(BaseModel):
    run_id: str
    message: str


class ProcessRequest(BaseModel):
    runner_height_m: float = Field(default=1.75, ge=1.0, le=2.5, description="Runner height in metres")


class ProcessResponse(BaseModel):
    run_id: str
    status: RunStatus


class Event(BaseModel):
    type: str
    frame: int
    time_sec: float


class MetricsSummary(BaseModel):
    cadence: float = Field(description="Steps per minute")
    stride_length: float = Field(description="Approximate stride length in metres")
    vertical_oscillation: float = Field(description="Hip vertical displacement (normalised 0-1)")
    symmetry_score: float = Field(description="Left/right symmetry 0-1 (1 = perfect)")
    fatigue_frame: int | None = Field(description="Frame where fatigue was first detected")
    fatigue_time_sec: float | None = Field(description="Time in seconds where fatigue was first detected")
    overstriding_count: int = Field(description="Number of overstriding events detected")
    events: list[Event] = Field(default_factory=list)


class TimeSeriesPoint(BaseModel):
    frame: int
    time_sec: float
    value: float


class RunResult(BaseModel):
    run_id: str
    status: RunStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: MetricsSummary | None = None
    insights: list[str] = Field(default_factory=list)
    cadence_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    hip_y_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    left_ankle_y_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    right_ankle_y_over_time: list[TimeSeriesPoint] = Field(default_factory=list)
    error: str | None = None
