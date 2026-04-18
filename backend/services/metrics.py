"""Biomechanical metrics engine.

Computes cadence, stride length, vertical oscillation, symmetry, and
overstriding detection from a list of per-frame landmark dicts produced by
``services.pose``.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _col(frames: list[dict], key: str) -> np.ndarray:
    """Extract a named column from the frame list as a NumPy array."""
    return np.array([f[key] for f in frames], dtype=float)


def _smooth(arr: np.ndarray, window: int = 5) -> np.ndarray:
    """Simple uniform moving-average smoothing."""
    if len(arr) < window:
        return arr
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


# ---------------------------------------------------------------------------
# Cadence
# ---------------------------------------------------------------------------

def compute_cadence(
    frames: list[dict],
    fps: float,
    min_peak_distance_frames: int = 8,
) -> dict[str, Any]:
    """Compute overall cadence (steps per minute) from ankle Y peaks.

    Parameters
    ----------
    frames:
        Per-frame landmark dicts.
    fps:
        Video frames per second.
    min_peak_distance_frames:
        Minimum frame gap between consecutive foot strikes.

    Returns
    -------
    dict with keys:
        cadence_spm, left_peaks, right_peaks, total_steps
    """
    if not frames:
        return {"cadence_spm": 0.0, "left_peaks": [], "right_peaks": [], "total_steps": 0}

    left_y = _smooth(_col(frames, "left_ankle_y"))
    right_y = _smooth(_col(frames, "right_ankle_y"))

    # Ankle Y increases downward in normalised coords, so foot strike = local max
    left_peaks, _ = find_peaks(left_y, distance=min_peak_distance_frames, prominence=0.005)
    right_peaks, _ = find_peaks(right_y, distance=min_peak_distance_frames, prominence=0.005)

    total_steps = len(left_peaks) + len(right_peaks)
    duration_sec = len(frames) / fps
    cadence_spm = (total_steps / duration_sec * 60) if duration_sec > 0 else 0.0

    return {
        "cadence_spm": round(cadence_spm, 1),
        "left_peaks": left_peaks.tolist(),
        "right_peaks": right_peaks.tolist(),
        "total_steps": total_steps,
    }


# ---------------------------------------------------------------------------
# Vertical oscillation
# ---------------------------------------------------------------------------

def compute_vertical_oscillation(frames: list[dict]) -> float:
    """Compute normalised hip-centre vertical oscillation.

    Returns the mean peak-to-trough amplitude of the hip Y signal over
    individual gait cycles.  Units are normalised image coordinates (0–1).
    """
    if not frames:
        return 0.0

    hip_y = _smooth((_col(frames, "left_hip_y") + _col(frames, "right_hip_y")) / 2)

    peaks, _ = find_peaks(hip_y, distance=8, prominence=0.002)
    troughs, _ = find_peaks(-hip_y, distance=8, prominence=0.002)

    if len(peaks) == 0 or len(troughs) == 0:
        return float(np.ptp(hip_y))

    # Pair each peak with the nearest trough and average the amplitudes
    amplitudes: list[float] = []
    for p in peaks:
        dists = np.abs(troughs - p)
        nearest = troughs[np.argmin(dists)]
        amplitudes.append(abs(float(hip_y[p] - hip_y[nearest])))

    return round(float(np.mean(amplitudes)), 5) if amplitudes else round(float(np.ptp(hip_y)), 5)


# ---------------------------------------------------------------------------
# Stride length (approximate)
# ---------------------------------------------------------------------------

def compute_stride_length(
    frames: list[dict],
    cadence_result: dict[str, Any],
    fps: float,
    runner_height_m: float = 1.75,
) -> float:
    """Approximate stride length in metres.

    Uses the relationship: stride_length ≈ speed / (cadence / 120).
    Speed is estimated from the hip-to-ankle normalised distance as a proxy
    for body-height scale, combined with the runner's actual height.

    For MVP accuracy this is approximate; a calibrated camera or GPS trace
    would improve it significantly.
    """
    if not frames or cadence_result["cadence_spm"] == 0:
        return 0.0

    # Estimate body height in normalised coords (hip centre → ankle average)
    hip_y = (_col(frames, "left_hip_y") + _col(frames, "right_hip_y")) / 2
    ankle_y = (_col(frames, "left_ankle_y") + _col(frames, "right_ankle_y")) / 2
    body_height_norm = float(np.median(ankle_y - hip_y))
    if body_height_norm <= 0:
        body_height_norm = 0.5

    metres_per_norm = runner_height_m / body_height_norm

    # Max ankle separation ≈ one full stride width; multiply by 2 heuristic
    ankle_sep = np.abs(_col(frames, "left_ankle_x") - _col(frames, "right_ankle_x"))
    stride_length_m = float(np.percentile(ankle_sep, 90)) * metres_per_norm * 2.0

    return round(min(stride_length_m, 3.5), 2)  # cap at realistic max


# ---------------------------------------------------------------------------
# Symmetry
# ---------------------------------------------------------------------------

def compute_symmetry(cadence_result: dict[str, Any]) -> float:
    """Return a symmetry score in [0, 1] where 1.0 is perfectly symmetric.

    Based on the ratio of left-to-right foot-strike counts.
    """
    left = len(cadence_result["left_peaks"])
    right = len(cadence_result["right_peaks"])
    if left + right == 0:
        return 1.0
    score = 1.0 - abs(left - right) / (left + right)
    return round(max(0.0, score), 3)


# ---------------------------------------------------------------------------
# Overstriding detection
# ---------------------------------------------------------------------------

def detect_overstriding(frames: list[dict], cadence_result: dict[str, Any]) -> list[int]:
    """Detect frames where the foot lands significantly ahead of the hip.

    Overstriding is indicated when the landing ankle X position is further
    forward (in image coords) than the hip X, suggesting heel striking ahead
    of the centre of mass.

    Returns a list of frame indices where overstriding was detected.
    """
    all_peaks = sorted(
        [(p, "left") for p in cadence_result["left_peaks"]]
        + [(p, "right") for p in cadence_result["right_peaks"]]
    )

    overstride_frames: list[int] = []
    for peak_idx, side in all_peaks:
        if peak_idx >= len(frames):
            continue
        row = frames[peak_idx]
        ankle_x = row[f"{side}_ankle_x"]
        hip_x = row[f"{side}_hip_x"]

        # In side-view footage the runner moves right → left or left → right.
        # We flag when ankle_x differs from hip_x by more than a threshold.
        # A positive diff means the ankle is ahead of the hip (overstriding).
        if abs(ankle_x - hip_x) > 0.12:
            overstride_frames.append(frames[peak_idx]["frame"])

    return overstride_frames


# ---------------------------------------------------------------------------
# Sliding-window cadence time series
# ---------------------------------------------------------------------------

def cadence_over_time(
    frames: list[dict],
    fps: float,
    window_sec: float = 10.0,
    step_sec: float = 5.0,
) -> list[dict[str, float]]:
    """Compute cadence in a sliding window across the video.

    Returns a list of ``{"frame": int, "time_sec": float, "value": float}``
    dicts suitable for charting.
    """
    if not frames:
        return []

    window = int(window_sec * fps)
    step = int(step_sec * fps)
    results: list[dict[str, float]] = []

    for start in range(0, len(frames) - window + 1, step):
        chunk = frames[start : start + window]
        local = compute_cadence(chunk, fps)
        mid_frame = frames[start + window // 2]["frame"]
        results.append(
            {
                "frame": mid_frame,
                "time_sec": round(mid_frame / fps, 2),
                "value": local["cadence_spm"],
            }
        )

    return results


# ---------------------------------------------------------------------------
# Hip Y time series (for vertical oscillation chart)
# ---------------------------------------------------------------------------

def hip_y_over_time(frames: list[dict], fps: float, downsample: int = 3) -> list[dict[str, float]]:
    """Return smoothed hip-centre Y signal downsampled for the UI chart."""
    if not frames:
        return []

    hip_y = _smooth((_col(frames, "left_hip_y") + _col(frames, "right_hip_y")) / 2, window=7)

    results: list[dict[str, float]] = []
    for i, row in enumerate(frames):
        if i % downsample == 0:
            results.append(
                {
                    "frame": row["frame"],
                    "time_sec": round(row["time_sec"], 3),
                    "value": round(float(hip_y[i]), 5),
                }
            )
    return results


# ---------------------------------------------------------------------------
# Ankle Y time series (for foot-strike chart)
# ---------------------------------------------------------------------------

def ankle_y_over_time(
    frames: list[dict],
    fps: float,
    side: str = "left",
    downsample: int = 2,
) -> list[dict[str, float]]:
    """Return ankle Y signal for one side, downsampled for the UI chart."""
    if not frames:
        return []

    ankle_y = _smooth(_col(frames, f"{side}_ankle_y"), window=5)
    results: list[dict[str, float]] = []

    for i, row in enumerate(frames):
        if i % downsample == 0:
            results.append(
                {
                    "frame": row["frame"],
                    "time_sec": round(row["time_sec"], 3),
                    "value": round(float(ankle_y[i]), 5),
                }
            )
    return results
