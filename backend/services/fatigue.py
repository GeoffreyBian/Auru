"""Fatigue detection service.

Analyses the sliding-window cadence series to detect the onset of fatigue,
defined as the first window where cadence drops more than ``threshold`` below
the baseline (first-window) cadence.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.05  # 5 % drop triggers fatigue flag


def detect_fatigue(
    cadence_series: list[dict[str, float]],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """Detect the onset of fatigue from a cadence time series.

    Parameters
    ----------
    cadence_series:
        List of ``{"frame", "time_sec", "value"}`` dicts from
        ``metrics.cadence_over_time``.
    threshold:
        Fractional drop below baseline that constitutes fatigue (default 5 %).

    Returns
    -------
    dict with keys:
        fatigue_detected, fatigue_frame, fatigue_time_sec,
        baseline_cadence, cadence_at_fatigue, drop_fraction
    """
    if len(cadence_series) < 2:
        return {
            "fatigue_detected": False,
            "fatigue_frame": None,
            "fatigue_time_sec": None,
            "baseline_cadence": None,
            "cadence_at_fatigue": None,
            "drop_fraction": None,
        }

    baseline = cadence_series[0]["value"]
    if baseline == 0:
        return {
            "fatigue_detected": False,
            "fatigue_frame": None,
            "fatigue_time_sec": None,
            "baseline_cadence": 0,
            "cadence_at_fatigue": None,
            "drop_fraction": None,
        }

    # Skip the first window (that *is* the baseline) and search forward
    for point in cadence_series[1:]:
        drop = (baseline - point["value"]) / baseline
        if drop >= threshold:
            logger.info(
                "Fatigue detected at frame %d (%.1f sec): cadence %.1f → %.1f (%.1f%% drop)",
                point["frame"],
                point["time_sec"],
                baseline,
                point["value"],
                drop * 100,
            )
            return {
                "fatigue_detected": True,
                "fatigue_frame": int(point["frame"]),
                "fatigue_time_sec": float(point["time_sec"]),
                "baseline_cadence": float(baseline),
                "cadence_at_fatigue": float(point["value"]),
                "drop_fraction": round(drop, 4),
            }

    return {
        "fatigue_detected": False,
        "fatigue_frame": None,
        "fatigue_time_sec": None,
        "baseline_cadence": float(baseline),
        "cadence_at_fatigue": None,
        "drop_fraction": None,
    }
