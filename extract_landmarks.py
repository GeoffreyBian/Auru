import cv2
from mediapipe.python.solutions import pose as mp_pose_module
import pandas as pd

VIDEO_PATH = "input.mp4"
OUTPUT_CSV = "output.csv"

mp_pose = mp_pose_module
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

cap = cv2.VideoCapture(VIDEO_PATH)

rows = []
frame_num = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        rows.append({
            "frame": frame_num,

            "left_ankle_x": lm[mp_pose.PoseLandmark.LEFT_ANKLE].x,
            "left_ankle_y": lm[mp_pose.PoseLandmark.LEFT_ANKLE].y,
            "right_ankle_x": lm[mp_pose.PoseLandmark.RIGHT_ANKLE].x,
            "right_ankle_y": lm[mp_pose.PoseLandmark.RIGHT_ANKLE].y,

            "left_hip_x": lm[mp_pose.PoseLandmark.LEFT_HIP].x,
            "left_hip_y": lm[mp_pose.PoseLandmark.LEFT_HIP].y,
            "right_hip_x": lm[mp_pose.PoseLandmark.RIGHT_HIP].x,
            "right_hip_y": lm[mp_pose.PoseLandmark.RIGHT_HIP].y,

            "left_knee_x": lm[mp_pose.PoseLandmark.LEFT_KNEE].x,
            "left_knee_y": lm[mp_pose.PoseLandmark.LEFT_KNEE].y,
            "right_knee_x": lm[mp_pose.PoseLandmark.RIGHT_KNEE].x,
            "right_knee_y": lm[mp_pose.PoseLandmark.RIGHT_KNEE].y,
        })

    frame_num += 1

cap.release()

pd.DataFrame(rows).to_csv(OUTPUT_CSV, index=False)
print(f"Saved landmarks to {OUTPUT_CSV}")