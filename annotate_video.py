import cv2
# If `mp.solutions.pose` fails on newer MediaPipe installs, use:
from mediapipe.python.solutions import pose as mp_pose_module

VIDEO_PATH = "input.mp4"
OUTPUT_VIDEO = "annotated.mp4"

mp_pose = mp_pose_module
from mediapipe.python.solutions import drawing_utils as mp_draw

pose = mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

cap = cv2.VideoCapture(VIDEO_PATH)

fps = int(cap.get(cv2.CAP_PROP_FPS))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

writer = cv2.VideoWriter(
    OUTPUT_VIDEO,
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (width, height)
)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    if result.pose_landmarks:
        mp_draw.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
        )

    writer.write(frame)

cap.release()
writer.release()

print(f"Saved annotated video to {OUTPUT_VIDEO}")