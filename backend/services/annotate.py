"""Polished video annotation service.

Reads saved per-frame landmarks from the analysis JSON and renders a
broadcast-style overlay onto the original video:

  Layer 1 – Original frame (untouched)
  Layer 2 – Skeleton (joints + bones, color-coded)
  Layer 3 – Foot-strike pulse circles
  Layer 4 – Metrics HUD (top-left, semi-transparent)
  Layer 5 – Event badge (top-center, fade in/out)
  Layer 6 – Progress bar (bottom strip, event markers)

No pose re-detection is performed; all data comes from the stored JSON.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .storage import OutputStore, VideoStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palette  (BGR for OpenCV)
# ---------------------------------------------------------------------------
_EMERALD    = (129, 185, 16)    # #10b981  — normal skeleton / progress
_INDIGO     = (235, 101, 99)    # #6366f1  — right-side skeleton
_RED        = (68,  68,  239)   # #ef4444  — overstride highlight
_AMBER      = (11,  158, 245)   # #f59e0b  — fatigue warning
_ORANGE     = (22,  115, 249)   # #f97316  — event dot on progress bar
_WHITE      = (255, 255, 255)
_BLACK      = (0,   0,   0)
_DARK       = (15,  15,  20)    # near-black for HUD backing

# Skeleton connections  (name_a, name_b, left_side?)
_BONES = [
    ("left_shoulder",  "right_shoulder", None),    # cross-body
    ("left_shoulder",  "left_hip",       True),
    ("right_shoulder", "right_hip",      False),
    ("left_hip",       "right_hip",      None),    # cross-body
    ("left_hip",       "left_knee",      True),
    ("left_knee",      "left_ankle",     True),
    ("right_hip",      "right_knee",     False),
    ("right_knee",     "right_ankle",    False),
]

_JOINT_SIDES: dict[str, bool | None] = {
    "left_shoulder":  True,
    "right_shoulder": False,
    "left_hip":       True,
    "right_hip":      False,
    "left_knee":      True,
    "right_knee":     False,
    "left_ankle":     True,
    "right_ankle":    False,
}


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _rounded_rect(img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                  r: int, color: tuple) -> None:
    """Fill a rounded rectangle (no border)."""
    cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
    cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
    for cx, cy in [(x1+r, y1+r), (x2-r, y1+r), (x1+r, y2-r), (x2-r, y2-r)]:
        cv2.circle(img, (cx, cy), r, color, -1)


def _text_shadow(img: np.ndarray, text: str, org: tuple[int, int],
                 font: int, scale: float, color: tuple, thickness: int) -> None:
    """Render text with a 1-pixel drop shadow for legibility."""
    cv2.putText(img, text, (org[0]+1, org[1]+1), font, scale,
                _BLACK, thickness + 1, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, color, thickness, cv2.LINE_AA)


def _lm_px(row: dict, name: str, w: int, h: int) -> tuple[int, int] | None:
    """Convert normalised landmark coords to pixel coordinates."""
    x = row.get(f"{name}_x")
    y = row.get(f"{name}_y")
    if x is None or y is None:
        return None
    return (int(x * w), int(y * h))


# ---------------------------------------------------------------------------
# Layer drawers
# ---------------------------------------------------------------------------

def _draw_skeleton(frame: np.ndarray, row: dict,
                   overstride: bool, scale: float) -> None:
    """Draw the pose skeleton on *frame* in-place."""
    w, h = frame.shape[1], frame.shape[0]
    bone_thick = max(1, int(2 * scale))
    joint_r    = max(3, int(5 * scale))
    shadow_r   = joint_r + 2

    # Bones
    for a, b, left_side in _BONES:
        pa = _lm_px(row, a, w, h)
        pb = _lm_px(row, b, w, h)
        if pa is None or pb is None:
            continue
        if overstride:
            color = _RED
        elif left_side is True:
            color = _EMERALD
        elif left_side is False:
            color = _INDIGO
        else:
            # cross-body bone: blend — use white at reduced intensity
            color = (200, 200, 200)
        # Shadow line
        cv2.line(frame, pa, pb, _BLACK, bone_thick + 2, cv2.LINE_AA)
        # Main line
        cv2.line(frame, pa, pb, color, bone_thick, cv2.LINE_AA)

    # Joints
    for name, left_side in _JOINT_SIDES.items():
        pt = _lm_px(row, name, w, h)
        if pt is None:
            continue
        if overstride:
            fill = _RED
        elif left_side:
            fill = _EMERALD
        else:
            fill = _INDIGO
        cv2.circle(frame, pt, shadow_r, _BLACK, -1)
        cv2.circle(frame, pt, joint_r,  fill,   -1)
        # Tiny bright centre dot for crispness
        cv2.circle(frame, pt, max(1, joint_r // 3), _WHITE, -1)


def _draw_foot_strikes(frame: np.ndarray, row: dict,
                       left_age: int, right_age: int,
                       max_age: int, scale: float) -> None:
    """Draw a fading pulse circle beneath each ankle at foot contact."""
    w, h = frame.shape[1], frame.shape[0]

    for side, color, age in [("left", _EMERALD, left_age),
                              ("right", _INDIGO,  right_age)]:
        if age <= 0:
            continue
        pt = _lm_px(row, f"{side}_ankle", w, h)
        if pt is None:
            continue

        frac    = age / max_age                       # 1 → 0 as it fades
        alpha   = frac * 0.75
        radius  = int((8 + (1 - frac) * 14) * scale) # expands as it fades

        # Draw the pulse on a temporary overlay for alpha blending
        overlay = frame.copy()
        cv2.circle(overlay, pt, radius, color, 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _draw_hud(frame: np.ndarray, cadence: float, symmetry: float,
              vo: float, scale: float) -> None:
    """Render the metrics HUD in the top-left corner."""
    pad   = int(14 * scale)
    lh    = int(22 * scale)          # line height
    fw    = int(190 * scale)         # box width
    fh    = int(lh * 3 + pad * 2)   # box height
    r     = int(8 * scale)           # corner radius
    fs    = 0.48 * scale             # font scale
    thick = max(1, int(scale))

    x1, y1 = pad, pad
    x2, y2 = x1 + fw, y1 + fh

    # Semi-transparent dark backing
    overlay = frame.copy()
    _rounded_rect(overlay, x1, y1, x2, y2, r, _DARK)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

    # Thin emerald top accent line
    cv2.rectangle(frame, (x1 + r, y1), (x2 - r, y1 + 2), _EMERALD, -1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    tx   = x1 + pad
    rows = [
        ("CADENCE",  f"{cadence:.0f} spm"),
        ("SYMMETRY", f"{symmetry * 100:.0f}%"),
        ("VERT OSC", f"{vo * 1000:.1f} mm"),
    ]
    for i, (label, value) in enumerate(rows):
        ty = y1 + pad + lh // 2 + i * lh + int(lh * 0.65)
        # Dim label
        _text_shadow(frame, label, (tx, ty), font, fs * 0.75,
                     (160, 160, 160), thick)
        # Bright value — right-aligned within box
        (vw, _), _ = cv2.getTextSize(value, font, fs, thick)
        _text_shadow(frame, value, (x2 - pad - vw, ty), font, fs,
                     _WHITE, thick)

    # Tiny "AURU" wordmark bottom-right of HUD
    mark_scale = fs * 0.6
    (mw, _), _ = cv2.getTextSize("AURU", font, mark_scale, 1)
    cv2.putText(frame, "AURU", (x2 - pad - mw, y2 - int(4 * scale)),
                font, mark_scale, _EMERALD, 1, cv2.LINE_AA)


def _draw_event_badge(frame: np.ndarray, text: str, color: tuple,
                      alpha: float, scale: float) -> None:
    """Render a centred, pill-shaped event badge near the top of the frame."""
    if alpha <= 0:
        return
    w, h   = frame.shape[1], frame.shape[0]
    font   = cv2.FONT_HERSHEY_SIMPLEX
    fs     = 0.55 * scale
    thick  = max(1, int(scale))
    pad_x  = int(18 * scale)
    pad_y  = int(10 * scale)
    r      = int(12 * scale)

    (tw, th), _ = cv2.getTextSize(text, font, fs, thick)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    bx = (w - bw) // 2
    by = int(18 * scale)

    # Badge background
    overlay = frame.copy()
    # Dark shadow ring
    _rounded_rect(overlay, bx - 2, by - 2, bx + bw + 2, by + bh + 2, r + 2, _BLACK)
    # Coloured fill
    bg = tuple(int(c * 0.25) for c in color)  # dark tinted version
    _rounded_rect(overlay, bx, by, bx + bw, by + bh, r, bg)
    # Coloured border
    cv2.rectangle(overlay, (bx + r, by), (bx + bw - r, by + 2), color, -1)
    cv2.rectangle(overlay, (bx + r, by + bh - 2), (bx + bw - r, by + bh), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # Text on top (drawn directly at alpha)
    tx = bx + pad_x
    ty = by + pad_y + th
    cv2.putText(frame, text, (tx + 1, ty + 1), font, fs, _BLACK, thick + 1, cv2.LINE_AA)
    text_overlay = frame.copy()
    cv2.putText(text_overlay, text, (tx, ty), font, fs, color, thick, cv2.LINE_AA)
    cv2.addWeighted(text_overlay, alpha, frame, 1 - alpha, 0, frame)


def _draw_progress_bar(frame: np.ndarray, frame_num: int, total: int,
                       event_frames: list[dict], fps: float, scale: float) -> None:
    """Draw a thin progress bar along the bottom edge with event markers."""
    w, h   = frame.shape[1], frame.shape[0]
    bar_h  = max(4, int(5 * scale))
    y1     = h - bar_h
    filled = int(w * frame_num / max(total, 1))

    # Background
    cv2.rectangle(frame, (0, y1), (w, h), (30, 30, 30), -1)
    # Progress fill
    if filled > 0:
        cv2.rectangle(frame, (0, y1), (filled, h), _EMERALD, -1)

    # Event markers — small diamonds
    marker_h = bar_h + int(6 * scale)
    for ev in event_frames:
        ef = ev.get("frame", 0)
        ex = int(w * ef / max(total, 1))
        color = _AMBER if ev.get("type") == "fatigue" else _RED
        pts = np.array([
            [ex,              y1 - marker_h // 2],
            [ex + marker_h // 2, y1],
            [ex,              y1 + bar_h],
            [ex - marker_h // 2, y1],
        ], np.int32)
        cv2.fillPoly(frame, [pts], color)

    # Timestamp  (bottom-right)
    font  = cv2.FONT_HERSHEY_SIMPLEX
    ts    = frame_num / fps
    mins  = int(ts // 60)
    secs  = int(ts % 60)
    label = f"{mins}:{secs:02d}"
    fs    = 0.38 * scale
    (tw, _), _ = cv2.getTextSize(label, font, fs, 1)
    cv2.putText(frame, label, (w - tw - int(6 * scale), y1 - int(4 * scale)),
                font, fs, (180, 180, 180), 1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Cadence interpolation
# ---------------------------------------------------------------------------

def _cadence_at_frame(cadence_ts: list[dict], frame_num: int) -> float:
    """Linearly interpolate cadence from the time-series for *frame_num*."""
    if not cadence_ts:
        return 0.0
    if frame_num <= cadence_ts[0]["frame"]:
        return cadence_ts[0]["value"]
    if frame_num >= cadence_ts[-1]["frame"]:
        return cadence_ts[-1]["value"]
    for i in range(len(cadence_ts) - 1):
        a, b = cadence_ts[i], cadence_ts[i + 1]
        if a["frame"] <= frame_num <= b["frame"]:
            t = (frame_num - a["frame"]) / max(b["frame"] - a["frame"], 1)
            return a["value"] + t * (b["value"] - a["value"])
    return cadence_ts[-1]["value"]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_annotated_video(run_id: str) -> Path:
    """Render a polished annotated video for *run_id* and save it to disk.

    Reads saved landmarks from the analysis JSON — no pose re-detection.

    Parameters
    ----------
    run_id:
        Identifier for a completed analysis run.

    Returns
    -------
    Path to the written annotated video file.
    """
    data = OutputStore.load(run_id)
    if data is None:
        raise FileNotFoundError(f"No analysis output found for run_id={run_id}")

    # ── unpack everything we need ──────────────────────────────────────────
    meta          = data.get("metadata", {})
    fps: float    = meta.get("fps", 30.0)
    total_frames  = meta.get("total_frames", 0)
    metrics       = data.get("metrics", {})
    cadence_ts    = data.get("cadence_over_time", [])
    raw_lm        = data.get("frame_landmarks", [])
    strike_left   = set(data.get("foot_strike_left", []))
    strike_right  = set(data.get("foot_strike_right", []))
    overstride_fs = set(data.get("overstride_frame_list", []))
    events        = metrics.get("events", [])

    overall_cadence  = metrics.get("cadence", 0.0)
    overall_symmetry = metrics.get("symmetry_score", 1.0)
    overall_vo       = metrics.get("vertical_oscillation", 0.0)

    if not raw_lm:
        raise ValueError("No frame landmarks in analysis output — cannot annotate.")

    # Build a lookup: frame_number → landmark row
    lm_by_frame: dict[int, dict] = {row["frame"]: row for row in raw_lm}

    # ── open source video ──────────────────────────────────────────────────
    video_path = VideoStore.path(run_id)
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found for run_id={run_id}")

    cap = cv2.VideoCapture(str(video_path))
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS) or fps

    # Scale factor relative to 720p so overlays look good at any resolution
    scale = min(width, height) / 720.0
    scale = max(0.5, min(scale, 3.0))  # clamp to sensible range

    # ── output writer ──────────────────────────────────────────────────────
    out_path = VideoStore.path(run_id, extension="annotated.mp4")
    # avc1 = H.264, required for browser playback; falls back to mp4v on
    # systems without a hardware encoder (video will still save, just not
    # playable in all browsers without a re-encode step).
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(str(out_path), fourcc, actual_fps, (width, height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, actual_fps, (width, height))
        logger.warning("avc1 unavailable — falling back to mp4v (may not play in all browsers)")
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open VideoWriter for {out_path}")

    # ── event badge state ─────────────────────────────────────────────────
    # Each active badge: {text, color, frames_remaining, total_frames}
    _BADGE_DURATION = int(actual_fps * 2.5)   # 2.5 s display
    _FADE_FRAMES    = int(actual_fps * 0.4)    # 0.4 s fade
    active_badges: list[dict] = []

    # Pre-index events by frame for O(1) lookup
    event_by_frame: dict[int, dict] = {e["frame"]: e for e in events}

    # Foot-strike age counters (frames since last strike)
    STRIKE_MAX = int(actual_fps * 0.6)  # glow lasts 0.6 s
    left_strike_age  = 0
    right_strike_age = 0

    # ── main loop ─────────────────────────────────────────────────────────
    frame_num = 0
    last_row: dict | None = None  # carry-forward for missed detections

    logger.info("Annotating video for run_id=%s (%dx%d @ %.1f fps)",
                run_id, width, height, actual_fps)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # ── get landmarks (carry forward if not detected this frame) ───────
        row = lm_by_frame.get(frame_num, last_row)
        if row is not None:
            last_row = row

        # ── trigger new event badges ───────────────────────────────────────
        if frame_num in event_by_frame:
            ev = event_by_frame[frame_num]
            if ev["type"] == "fatigue":
                text  = "\u26a0  FATIGUE DETECTED"
                color = _AMBER
            else:
                text  = "\u25cf  OVERSTRIDING"
                color = _RED
            active_badges.append({
                "text":       text,
                "color":      color,
                "remaining":  _BADGE_DURATION,
                "total":      _BADGE_DURATION,
            })

        # ── foot-strike age tracking ───────────────────────────────────────
        if frame_num in strike_left:
            left_strike_age = STRIKE_MAX
        elif left_strike_age > 0:
            left_strike_age -= 1

        if frame_num in strike_right:
            right_strike_age = STRIKE_MAX
        elif right_strike_age > 0:
            right_strike_age -= 1

        # ── LAYER 2 — skeleton ─────────────────────────────────────────────
        if row is not None:
            _draw_skeleton(frame, row, frame_num in overstride_fs, scale)

        # ── LAYER 3 — foot-strike pulse ────────────────────────────────────
        if row is not None:
            _draw_foot_strikes(frame, row,
                               left_strike_age, right_strike_age,
                               STRIKE_MAX, scale)

        # ── LAYER 4 — metrics HUD ──────────────────────────────────────────
        live_cadence = _cadence_at_frame(cadence_ts, frame_num) or overall_cadence
        _draw_hud(frame, live_cadence, overall_symmetry, overall_vo, scale)

        # ── LAYER 5 — event badges ─────────────────────────────────────────
        for badge in active_badges:
            rem   = badge["remaining"]
            total = badge["total"]
            # Fade in during first _FADE_FRAMES, full, then fade out
            if rem > total - _FADE_FRAMES:
                alpha = (total - rem) / _FADE_FRAMES
            elif rem < _FADE_FRAMES:
                alpha = rem / _FADE_FRAMES
            else:
                alpha = 1.0
            _draw_event_badge(frame, badge["text"], badge["color"],
                              min(alpha, 0.95), scale)

        # Decrement badge timers and remove expired ones
        active_badges = [b for b in active_badges if b["remaining"] > 0]
        for b in active_badges:
            b["remaining"] -= 1

        # ── LAYER 6 — progress bar ─────────────────────────────────────────
        _draw_progress_bar(frame, frame_num, total_frames or frame_num + 1,
                           events, actual_fps, scale)

        writer.write(frame)
        frame_num += 1

    cap.release()
    writer.release()

    logger.info("Annotated video written to %s (%d frames)", out_path.name, frame_num)
    return out_path
