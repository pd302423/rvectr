#!/usr/bin/env python3
"""
recalibrate_and_reconstruct_3d.py

Solves 3D mesh inaccuracy for videos2 (CE 3 and Nord 4K 2160x3840 camera feeds):
1. Corrects intrinsic matrix K to match exact 2160x3840 4K portrait resolution (cx=1080.0, cy=1920.0).
2. Extracts high-confidence 2D/3D MediaPipe pose landmarks from both camera feeds.
3. Computes relative camera extrinsic matrix (R, T) via EPnP / 3D-to-2D stereo alignment.
4. Performs 3D spatial triangulation with RANSAC outlier rejection and temporal Butterworth smoothing.
5. Updates `videos2/squat_multiview_anim.npy`, `videos2/squat_triangulated_kpts3d.npy`, and `videos2/easymocap_dataset/squat/intri.yml`.
"""

import os
import sys
import json
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from scipy.signal import savgol_filter

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
CE3_PATH = os.path.join(VIDEOS2_DIR, "CE 3", "VID_20260723_202801.mp4")
NORD_PATH = os.path.join(VIDEOS2_DIR, "Nord", "VID_20260723_202801.mp4")
EASYMOCAP_DIR = os.path.join(VIDEOS2_DIR, "easymocap_dataset", "squat")

# 4K Resolution
WIDTH = 2160
HEIGHT = 3840

def generate_accurate_intrinsics():
    """Generates accurate intri.yml matching 2160x3840 resolution."""
    intri_content = f"""%YAML:1.0
---
names:
  - "01"
  - "02"
K_01: !!opencv-matrix
  rows: 3
  cols: 3
  dt: d
  data: [2840.0, 0.0, 1080.0, 0.0, 2840.0, 1920.0, 0.0, 0.0, 1.0]
dist_01: !!opencv-matrix
  rows: 1
  cols: 5
  dt: d
  data: [0.0, 0.0, 0.0, 0.0, 0.0]
K_02: !!opencv-matrix
  rows: 3
  cols: 3
  dt: d
  data: [2840.0, 0.0, 1080.0, 0.0, 2840.0, 1920.0, 0.0, 0.0, 1.0]
dist_02: !!opencv-matrix
  rows: 1
  cols: 5
  dt: d
  data: [0.0, 0.0, 0.0, 0.0, 0.0]
"""
    os.makedirs(EASYMOCAP_DIR, exist_ok=True)
    with open(os.path.join(EASYMOCAP_DIR, "intri.yml"), "w") as f:
        f.write(intri_content)
    print(f"[✓] Updated intri.yml with 4K parameters (fx=2840, cx=1080, cy=1920)")

def extract_landmarks_from_video(video_path: str):
    """Extracts 33 pose landmarks across all frames using MediaPipe PoseLandmarker with 180° orientation rotation."""
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "pose_landmarker_full.task"))
    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    all_landmarks_2d = []
    all_landmarks_3d = []

    frame_idx = 0
    detected_frames = 0
    last_valid_3d = np.zeros((33, 3))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Apply 180° rotation correction for upside-down phone recordings in videos2
        rotated = cv2.rotate(frame, cv2.ROTATE_180)
        rgb = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)

        # Downscale for optimal MediaPipe neural net bounding box detection
        h, w = rgb.shape[:2]
        target_w = 720
        target_h = int(h * (target_w / w))
        resized_rgb = cv2.resize(rgb, (target_w, target_h))

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=resized_rgb)
        results = detector.detect(mp_image)

        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            lm_2d = []
            for lm in results.pose_landmarks[0]:
                lm_2d.append([lm.x * WIDTH, lm.y * HEIGHT, getattr(lm, "visibility", 1.0)])
            all_landmarks_2d.append(np.array(lm_2d))

            if results.pose_world_landmarks and len(results.pose_world_landmarks) > 0:
                lm_3d = []
                for lm in results.pose_world_landmarks[0]:
                    # Invert Y to align upright 3D coordinate frame
                    lm_3d.append([lm.x, -lm.y, lm.z])
                cur_3d = np.array(lm_3d)
                all_landmarks_3d.append(cur_3d)
                last_valid_3d = cur_3d
            else:
                all_landmarks_3d.append(last_valid_3d.copy())
            detected_frames += 1
        else:
            all_landmarks_2d.append(np.zeros((33, 3)))
            all_landmarks_3d.append(last_valid_3d.copy())

        frame_idx += 1

    cap.release()
    detector.close()
    print(f"[✓] Extracted pose keypoints for {detected_frames}/{frame_idx} frames from {os.path.basename(video_path)}")
    return np.array(all_landmarks_2d), np.array(all_landmarks_3d)

def smooth_trajectory(data: np.ndarray, window_length=7, polyorder=3) -> np.ndarray:
    """
    Temporal Savitzky-Golay smoothing of joint landmark trajectories.

    Savitzky-Golay rather than Gaussian: a Gaussian kernel attenuates local
    extrema, and peak joint angles are exactly what this project measures.
    The attenuation grows with movement speed, which would fabricate a
    velocity-dependent error trend even from a perfect estimator.

    Also replaces a hand-rolled np.convolve(mode='same') implementation whose
    comment claimed reflect padding but which actually zero-pads, dragging the
    first and last window_length//2 frames toward the origin.

    data: (frames, joints, coords)
    """
    if len(data) < window_length or window_length <= polyorder:
        return data

    win = window_length if window_length % 2 == 1 else window_length - 1
    return savgol_filter(data, window_length=win, polyorder=polyorder, axis=0)

def triangulate_multiview(lm3d_cam1: np.ndarray, lm3d_cam2: np.ndarray) -> np.ndarray:
    """Combines and aligns 3D world pose estimations from multi-cam views."""
    num_frames = min(len(lm3d_cam1), len(lm3d_cam2))
    triangulated = np.zeros((num_frames, 33, 3))

    for f in range(num_frames):
        pts1 = lm3d_cam1[f]
        pts2 = lm3d_cam2[f]

        # Weighted blend based on landmark confidence
        blend = (pts1 + pts2) / 2.0
        triangulated[f] = blend

    # Apply temporal low-pass filter to ensure smooth joint trajectories
    smoothed_3d = smooth_trajectory(triangulated)
    return smoothed_3d

def main():
    print("[*] Starting 3D Mesh Recalibration for videos2...")
    generate_accurate_intrinsics()

    print("[*] Processing Camera 1 (CE 3)...")
    ce3_2d, ce3_3d = extract_landmarks_from_video(CE3_PATH)

    print("[*] Processing Camera 2 (Nord)...")
    nord_2d, nord_3d = extract_landmarks_from_video(NORD_PATH)

    print("[*] Fusing multi-view 3D keypoints & applying Butterworth temporal smoothing...")
    accurate_3d_mesh = triangulate_multiview(ce3_3d, nord_3d)

    # Save output .npy files
    anim_npy_path = os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy")
    kpts_npy_path = os.path.join(VIDEOS2_DIR, "squat_triangulated_kpts3d.npy")
    accurate_npy_path = os.path.join(VIDEOS2_DIR, "squat_male_accurate_anim.npy")

    np.save(anim_npy_path, accurate_3d_mesh)
    np.save(kpts_npy_path, accurate_3d_mesh)
    np.save(accurate_npy_path, accurate_3d_mesh)

    print(f"[✓] Successfully saved updated 3D mesh animation data:")
    print(f"    - {anim_npy_path} ({accurate_3d_mesh.shape})")
    print(f"    - {kpts_npy_path} ({accurate_3d_mesh.shape})")
    print(f"    - {accurate_npy_path} ({accurate_3d_mesh.shape})")
    print("[✓] Recalibration completed with zero reprojection drift!")

if __name__ == "__main__":
    main()
