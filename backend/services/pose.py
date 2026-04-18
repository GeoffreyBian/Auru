"""Pose landmark extraction using MediaPipe Tasks API (mediapipe >= 0.10.30).

Takes a video file path and produces a list of per-frame landmark dicts
containing the key joints needed for biomechanical analysis.

The pose landmarker model is downloaded automatically on first use and cached
in ``data/models/``.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

logger = logging.getLogger(__name__)

# Model download — lite is fast; swap to "full" for higher accuracy at cost of speed
_MODEL_NAME = "pose_landmarker_full.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    f"pose_landmarker/pose_landmarker_full/float16/latest/{_MODEL_NAME}"
)
_MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
_MODEL_PATH = _MODELS_DIR / _MODEL_NAME

# Landmark indices in the 33-point MediaPipe pose model
_LANDMARK_INDICES = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


def _ensure_model() -> Path:
    """Download the pose landmarker model if it isn't already cached."""
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not _MODEL_PATH.exists():
        logger.info("Downloading pose landmarker model from %s …", _MODEL_URL)
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        logger.info("Model saved to %s", _MODEL_PATH)
    return _MODEL_PATH


def _landmarks_to_row(landmarks, frame_num: int, fps: float) -> dict:
    """Flatten the relevant landmarks into a plain dict for one frame."""
    row: dict = {"frame": frame_num, "time_sec": frame_num / fps}
    for name, idx in _LANDMARK_INDICES.items():
        pt = landmarks[idx]
        row[f"{name}_x"] = pt.x
        row[f"{name}_y"] = pt.y
        row[f"{name}_z"] = pt.z
        row[f"{name}_vis"] = pt.visibility
    return row


def extract_landmarks(video_path: str | Path) -> tuple[list[dict], dict]:
    """Extract pose landmarks for every frame in *video_path*.

    Parameters
    ----------
    video_path:
        Absolute path to the source video file.

    Returns
    -------
    landmarks:
        List of dicts, one per successfully detected frame.
    metadata:
        Video properties: ``fps``, ``total_frames``, ``width``, ``height``.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    model_path = _ensure_model()

    cap = cv2.VideoCapture(str(video_path))
    fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    metadata = {
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_sec": total_frames / fps if fps else 0,
    }

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    landmarks_out: list[dict] = []
    frame_num = 0

    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(frame_num / fps * 1000)

            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks:
                row = _landmarks_to_row(result.pose_landmarks[0], frame_num, fps)
                landmarks_out.append(row)

            frame_num += 1

    cap.release()

    logger.info(
        "Extracted landmarks from %d/%d frames in %s",
        len(landmarks_out),
        frame_num,
        video_path.name,
    )
    return landmarks_out, metadata
