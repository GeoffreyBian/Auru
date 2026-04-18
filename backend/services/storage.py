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
