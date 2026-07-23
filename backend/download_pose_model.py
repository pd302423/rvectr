import urllib.request
import os

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "pose_landmarker_full.task"))
url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"

if not os.path.exists(model_path):
    print(f"[*] Downloading MediaPipe Pose Landmarker Heavy model to {model_path}...")
    urllib.request.urlretrieve(url, model_path)
    print(f"[✓] Downloaded {os.path.getsize(model_path)} bytes.")
else:
    print(f"[✓] Model already exists at {model_path}")
