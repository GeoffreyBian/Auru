import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

FPS = 30
WINDOW_SEC = 10
WINDOW_FRAMES = FPS * WINDOW_SEC

RUNNER_HEIGHT_M = 1.75
BODY_SCALE = 1.0

df = pd.read_csv("output.csv")

# --- Cadence ---
left_peaks, _ = find_peaks(df["left_ankle_y"], distance=10)
right_peaks, _ = find_peaks(df["right_ankle_y"], distance=10)

steps = len(left_peaks) + len(right_peaks)
duration_sec = len(df) / FPS
cadence = steps / duration_sec * 60

# --- Vertical Oscillation ---
df["hip_y"] = (df["left_hip_y"] + df["right_hip_y"]) / 2
vertical_oscillation = df["hip_y"].max() - df["hip_y"].min()

# --- Symmetry ---
symmetry_score = abs(len(left_peaks) - len(right_peaks))

# --- Approximate Stride Length ---
# Estimate body width in normalized image coordinates
body_height_norm = abs(df["hip_y"].mean() - df[["left_ankle_y", "right_ankle_y"]].mean().mean())
meters_per_norm = RUNNER_HEIGHT_M / BODY_SCALE

# Estimate distance between left/right ankle x positions
ankle_sep = abs(df["left_ankle_x"] - df["right_ankle_x"])
approx_stride_length_m = ankle_sep.mean() * meters_per_norm * 2

# --- Sliding Window Cadence for Fatigue Detection ---
window_cadence = []
window_frames = []

for start in range(0, len(df) - WINDOW_FRAMES, WINDOW_FRAMES // 2):
    end = start + WINDOW_FRAMES
    chunk = df.iloc[start:end]

    peaks, _ = find_peaks(chunk["left_ankle_y"], distance=10)
    local_steps = len(peaks) * 2
    local_duration = len(chunk) / FPS

    local_cadence = local_steps / local_duration * 60

    window_cadence.append(local_cadence)
    window_frames.append(start + WINDOW_FRAMES // 2)

# --- Fatigue Detection ---
fatigue_frame = None
baseline = window_cadence[0] if len(window_cadence) > 0 else cadence

for frame, local_cadence in zip(window_frames, window_cadence):
    if local_cadence < baseline * 0.95:
        fatigue_frame = frame
        break

# --- Save Metrics ---
with open("metrics.txt", "w") as f:
    f.write(f"Cadence: {cadence:.1f} steps/min\n")
    f.write(f"Vertical Oscillation: {vertical_oscillation:.4f}\n")
    f.write(f"Symmetry Score: {symmetry_score}\n")
    f.write(f"Approximate Stride Length: {approx_stride_length_m:.2f} m\n")

    if fatigue_frame is not None:
        f.write(f"Fatigue detected around frame {fatigue_frame}\n")
    else:
        f.write("No fatigue detected\n")

print(open("metrics.txt").read())

# --- Plot 1: Foot Strikes ---
plt.figure(figsize=(10, 5))
plt.plot(df["frame"], df["left_ankle_y"], label="Left ankle Y")
plt.scatter(
    df["frame"].iloc[left_peaks],
    df["left_ankle_y"].iloc[left_peaks],
    color="red",
    label="Foot strikes"
)
plt.xlabel("Frame")
plt.ylabel("Ankle Y Position")
plt.title("Detected Foot Strikes")
plt.legend()
plt.savefig("cadence_plot.png")

# --- Plot 2: Fatigue / Cadence Drift ---
plt.figure(figsize=(10, 5))
plt.plot(window_frames, window_cadence, marker="o")

if fatigue_frame is not None:
    plt.axvline(fatigue_frame, linestyle="--")

plt.xlabel("Frame")
plt.ylabel("Cadence (steps/min)")
plt.title("Cadence Over Time")
plt.savefig("fatigue_plot.png")

print("Saved cadence_plot.png and fatigue_plot.png")