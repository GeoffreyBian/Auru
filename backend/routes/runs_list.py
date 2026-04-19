"""Runs list route — returns summaries of all completed runs."""

from __future__ import annotations

from fastapi import APIRouter

from services.storage import OutputStore

router = APIRouter()


@router.get("/runs", summary="List all completed runs")
async def list_runs() -> list[dict]:
    """Return summary metadata for every completed run, newest first."""
    return OutputStore.list_completed()
