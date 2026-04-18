"""Rule-based coaching insights engine.

Evaluates biomechanical metrics and returns plain-language coaching tips.
Designed to be easily extended with ML-based insights in future iterations.
"""

from __future__ import annotations

from typing import Any


# Thresholds based on published running biomechanics literature
_CADENCE_LOW = 160          # steps/min — below this is generally sub-optimal
_CADENCE_TARGET_MIN = 170   # elite range lower bound
_CADENCE_TARGET_MAX = 185   # elite range upper bound
_VO_HIGH = 0.045            # normalised hip oscillation — above this is excessive bounce
_SYMMETRY_WARN = 0.92       # below this score flags imbalance
_SYMMETRY_POOR = 0.80       # significant left/right asymmetry
_OVERSTRIDE_WARN = 3        # event count threshold


def generate_insights(
    metrics: dict[str, Any],
    fatigue: dict[str, Any],
    overstride_frames: list[int],
) -> list[str]:
    """Generate a list of plain-language coaching insights.

    Parameters
    ----------
    metrics:
        Output from the metrics engine (cadence, vertical_oscillation, etc.)
    fatigue:
        Output from fatigue detection service.
    overstride_frames:
        List of frame indices where overstriding was detected.

    Returns
    -------
    List of coaching insight strings, ordered by priority.
    """
    insights: list[str] = []

    cadence = metrics.get("cadence_spm", 0)
    vo = metrics.get("vertical_oscillation", 0)
    symmetry = metrics.get("symmetry_score", 1.0)

    # --- Cadence ---
    if cadence > 0:
        if cadence < _CADENCE_LOW:
            increase_pct = round((_CADENCE_TARGET_MIN - cadence) / cadence * 100)
            insights.append(
                f"Your cadence of {cadence:.0f} spm is below the optimal range. "
                f"Try increasing it by ~{increase_pct}% toward {_CADENCE_TARGET_MIN}–{_CADENCE_TARGET_MAX} spm — "
                "shorter, quicker steps reduce impact force and improve efficiency."
            )
        elif cadence < _CADENCE_TARGET_MIN:
            insights.append(
                f"Your cadence ({cadence:.0f} spm) is close to the optimal range. "
                f"A small increase of 5–8% toward {_CADENCE_TARGET_MIN} spm could further reduce injury risk."
            )
        elif cadence > _CADENCE_TARGET_MAX:
            insights.append(
                f"Your cadence ({cadence:.0f} spm) is in the elite range — great work maintaining turnover."
            )
        else:
            insights.append(
                f"Cadence of {cadence:.0f} spm is excellent — right in the optimal {_CADENCE_TARGET_MIN}–{_CADENCE_TARGET_MAX} spm window."
            )

    # --- Vertical oscillation ---
    if vo > _VO_HIGH:
        insights.append(
            f"Vertical oscillation is elevated ({vo:.3f} normalised). "
            "Excess vertical bounce wastes energy. Focus on forward lean from the ankles "
            "and avoid pushing off vertically."
        )
    elif vo > 0:
        insights.append(
            f"Vertical oscillation looks efficient ({vo:.3f} normalised) — "
            "your energy is directed forward, not upward."
        )

    # --- Symmetry ---
    if symmetry < _SYMMETRY_POOR:
        insights.append(
            f"Significant left/right asymmetry detected (score {symmetry:.2f}). "
            "This could indicate a muscular imbalance or compensation pattern. "
            "Consider single-leg strength work and consult a physio if discomfort persists."
        )
    elif symmetry < _SYMMETRY_WARN:
        insights.append(
            f"Mild left/right asymmetry noted (score {symmetry:.2f}). "
            "Monitor this over time — hip strengthening exercises can help equalise step timing."
        )
    else:
        insights.append(
            f"Left/right symmetry is good ({symmetry:.2f}). "
            "Your gait is well-balanced."
        )

    # --- Overstriding ---
    if len(overstride_frames) >= _OVERSTRIDE_WARN:
        insights.append(
            f"Overstriding detected on {len(overstride_frames)} foot strikes. "
            "Landing with your foot too far ahead of your hips increases braking forces. "
            "Try to land with your foot directly beneath your centre of mass."
        )
    elif overstride_frames:
        insights.append(
            f"Minor overstriding on {len(overstride_frames)} foot strikes — keep an eye on this."
        )

    # --- Fatigue ---
    if fatigue.get("fatigue_detected"):
        t = fatigue["fatigue_time_sec"]
        drop_pct = round(fatigue["drop_fraction"] * 100, 1)
        minutes = int(t // 60)
        seconds = int(t % 60)
        insights.append(
            f"Fatigue onset detected around {minutes}:{seconds:02d} into the run "
            f"(cadence dropped {drop_pct}% below baseline). "
            "Consider structured speed-endurance intervals to push this threshold further out."
        )
    else:
        insights.append(
            "No significant cadence fatigue detected — your pace held steady throughout."
        )

    return insights
