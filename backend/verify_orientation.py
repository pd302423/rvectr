#!/usr/bin/env python3
"""
verify_orientation.py
Verifies that Head/Shoulders are above Hips (Z > 0) and Knees/Ankles are below Hips (Z < 0).
"""
import os
import numpy as np

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
ANIM_NPY_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy")

motion_3d = np.load(ANIM_NPY_PATH)

for f_idx in [50, 100, 200, 300, 400]:
    frame = motion_3d[f_idx]

    # Correct 180° video flip for 3D world coordinates
    # In MediaPipe, raw Y is inverted due to upside-down camera
    x = frame[:, 0]
    y = frame[:, 1] # inverted Y
    z = frame[:, 2]

    # Convert to Blender Z-up coordinates
    bl_x = x
    bl_y = z
    bl_z = y # Y is up in world coords when correctly oriented

    bl_coords = np.column_stack([bl_x, bl_y, bl_z])
    hip_mid = (bl_coords[23] + bl_coords[24]) / 2.0
    bl_coords = bl_coords - hip_mid

    head_z = bl_coords[0][2]
    shoulder_z = (bl_coords[11][2] + bl_coords[12][2]) / 2.0
    knee_z = (bl_coords[25][2] + bl_coords[26][2]) / 2.0
    ankle_z = (bl_coords[27][2] + bl_coords[28][2]) / 2.0

    print(f"Frame {f_idx}: Head Z={head_z:.3f}m | Shoulders Z={shoulder_z:.3f}m | Hips Z=0.000m | Knees Z={knee_z:.3f}m | Ankles Z={ankle_z:.3f}m")
