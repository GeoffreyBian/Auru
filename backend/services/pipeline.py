"""End-to-end analysis pipeline.

Orchestrates pose extraction → metrics computation → fatigue detection →
coaching insights → output persistence → video annotation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .coaching import generate_insights
from .fatigue import detect_fatigue
from .metrics import (
    ankle_y_over_time,
    cadence_over_time,
    compute_cadence,
    compute_stride_length,
    compute_symmetry,
    compute_vertical_oscillation,
    detect_overstriding,
    hip_y_over_time,
)
from .pose import extract_landmarks
from .storage import OutputStore, VideoStore

logger = logging.getLogger(__name__)


def run_pipeline(run_id: str, runner_height_m: float = 1.75) -> dict[str, Any]:
    """Execute the full analysis pipeline for a given run.

    Parameters
    ----------
    run_id:
        Identifier that maps to a stored video file.
    runner_height_m:
        Subject's height in metres (used for stride length estimation).

    Returns
    -------
    Full result dict that is also persisted via ``OutputStore``.
    """
    video_path = VideoStore.path(run_id)
    if not video_path.exists():
        raise FileNotFoundError(f"No video found for run_id={run_id}")

    OutputStore.update_status(run_id, "processing")
    logger.info("Pipeline starting for run_id=%s", run_id)

    try:
        # 1. Pose extraction
        landmarks, metadata = extract_landmarks(video_path)
        fps = metadata["fps"]

        if len(landmarks) < 30:
            raise ValueError(
                f"Insufficient landmark frames ({len(landmarks)}). "
                "Check video quality and ensure the runner is fully visible."
            )

        # 2. Metrics
        cadence_result = compute_cadence(landmarks, fps)
        vo = compute_vertical_oscillation(landmarks)
        stride_m = compute_stride_length(landmarks, cadence_result, fps, runner_height_m)
        symmetry = compute_symmetry(cadence_result)
        overstride_frames = detect_overstriding(landmarks, cadence_result)

        # 3. Time series for charts
        cadence_ts = cadence_over_time(landmarks, fps)
        hip_ts = hip_y_over_time(landmarks, fps)
        left_ankle_ts = ankle_y_over_time(landmarks, fps, side="left")
        right_ankle_ts = ankle_y_over_time(landmarks, fps, side="right")

        # 4. Fatigue detection
        fatigue = detect_fatigue(cadence_ts)

        # 5. Build events list
        events: list[dict[str, Any]] = []
        if fatigue["fatigue_detected"]:
            events.append(
                {
                    "type": "fatigue",
                    "frame": fatigue["fatigue_frame"],
                    "time_sec": fatigue["fatigue_time_sec"],
                }
            )
        for frame in overstride_frames[:10]:
            events.append(
                {
                    "type": "overstride",
                    "frame": frame,
                    "time_sec": round(frame / fps, 2),
                }
            )

        # 6. Coaching
        metric_dict = {
            "cadence_spm": cadence_result["cadence_spm"],
            "vertical_oscillation": vo,
            "symmetry_score": symmetry,
        }
        insights = generate_insights(metric_dict, fatigue, overstride_frames)

        # 7. Assemble output — includes raw per-frame data needed for annotation
        result: dict[str, Any] = {
            "run_id": run_id,
            "status": "completed",
            "metadata": metadata,
            "metrics": {
                "cadence": cadence_result["cadence_spm"],
                "stride_length": stride_m,
                "vertical_oscillation": vo,
                "symmetry_score": symmetry,
                "fatigue_frame": fatigue["fatigue_frame"],
                "fatigue_time_sec": fatigue["fatigue_time_sec"],
                "overstriding_count": len(overstride_frames),
                "events": events,
            },
            "insights": insights,
            "cadence_over_time": cadence_ts,
            "hip_y_over_time": hip_ts,
            "left_ankle_y_over_time": left_ankle_ts,
            "right_ankle_y_over_time": right_ankle_ts,
            # Annotation data — per-frame landmarks and strike indices
            "frame_landmarks": landmarks,
            "foot_strike_left": cadence_result["left_peaks"],
            "foot_strike_right": cadence_result["right_peaks"],
            "overstride_frame_list": overstride_frames,
            "annotated_video_ready": False,
            "created_at": time.time(),
        }

        OutputStore.save(run_id, result)
        logger.info("Analysis completed for run_id=%s", run_id)
        # Annotation is triggered separately by the process route so that
        # metrics are immediately visible to the client via polling.
        return result

    except Exception as exc:
        logger.exception("Pipeline failed for run_id=%s: %s", run_id, exc)
        OutputStore.update_status(run_id, "failed", error=str(exc))
        raise
