"""Storage abstraction — local filesystem for MVP, swappable for S3 later.

All paths are resolved relative to the ``data/`` directory at project root.
To migrate to S3, replace the ``VideoStore`` and ``OutputStore`` classes with
implementations that speak to ``boto3`` while keeping the same interface.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

# Resolve data directory relative to this file's location: backend/services/ -> ../../data
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_VIDEOS_DIR = _DATA_DIR / "videos"
_OUTPUTS_DIR = _DATA_DIR / "outputs"

_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_run_id() -> str:
    """Return a new unique run identifier."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Video storage
# ---------------------------------------------------------------------------

class VideoStore:
    """Manages raw video files on local disk."""

    @staticmethod
    def save(run_id: str, data: bytes, extension: str = "mp4") -> Path:
        """Persist ``data`` bytes and return the saved path."""
        dest = _VIDEOS_DIR / f"{run_id}.{extension}"
        dest.write_bytes(data)
        return dest

    @staticmethod
    def path(run_id: str, extension: str = "mp4") -> Path:
        """Return the path for a stored video; does not check existence."""
        return _VIDEOS_DIR / f"{run_id}.{extension}"

    @staticmethod
    def exists(run_id: str, extension: str = "mp4") -> bool:
        """Check whether a video exists for this run."""
        return (_VIDEOS_DIR / f"{run_id}.{extension}").exists()


# ---------------------------------------------------------------------------
# Output / results storage
# ---------------------------------------------------------------------------

class OutputStore:
    """Manages analysis result JSON files on local disk."""

    @staticmethod
    def save(run_id: str, data: dict[str, Any]) -> Path:
        """Serialise ``data`` to JSON and return the saved path."""
        dest = _OUTPUTS_DIR / f"{run_id}.json"
        dest.write_text(json.dumps(data, indent=2))
        return dest

    @staticmethod
    def load(run_id: str) -> dict[str, Any] | None:
        """Load and return a result dict, or ``None`` if it doesn't exist."""
        path = _OUTPUTS_DIR / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    @staticmethod
    def exists(run_id: str) -> bool:
        """Return True if an output file exists for this run."""
        return (_OUTPUTS_DIR / f"{run_id}.json").exists()

    @staticmethod
    def update_status(run_id: str, status: str, error: str | None = None) -> None:
        """Update (or create) a stub output file with the given status."""
        existing = OutputStore.load(run_id) or {}
        existing["status"] = status
        if error is not None:
            existing["error"] = error
        OutputStore.save(run_id, existing)

    @staticmethod
    def list_completed() -> list[dict[str, Any]]:
        """Return summary dicts for all completed runs, newest first.

        Each dict contains: run_id, created_at, duration_sec, cadence,
        symmetry_score, annotated_video_ready.
        """
        summaries = []
        for path in sorted(_OUTPUTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            if data.get("status") != "completed":
                continue
            meta    = data.get("metadata", {})
            metrics = data.get("metrics", {})
            summaries.append({
                "run_id":               path.stem,
                "created_at":           data.get("created_at", path.stat().st_mtime),
                "duration_sec":         meta.get("duration_sec"),
                "fps":                  meta.get("fps"),
                "cadence":              metrics.get("cadence"),
                "symmetry_score":       metrics.get("symmetry_score"),
                "vertical_oscillation": metrics.get("vertical_oscillation"),
                "fatigue_time_sec":     metrics.get("fatigue_time_sec"),
                "overstriding_count":   metrics.get("overstriding_count", 0),
                "annotated_video_ready": data.get("annotated_video_ready", False),
            })
        return summaries
