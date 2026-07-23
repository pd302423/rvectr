#!/usr/bin/env python3
"""
test_upright_skeleton.py

Tests exact MediaPipe 3D landmark coordinate transformation into Blender 3D upright coordinate frame.
"""

import os
import sys
import numpy as np

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
ANIM_NPY_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy")

motion_3d = np.load(ANIM_NPY_PATH)
sample_frame = motion_3d[100] # frame 100

print(f"Sample frame shape: {sample_frame.shape}")
print(f"Hip Left (23): {sample_frame[23]}")
print(f"Hip Right (24): {sample_frame[24]}")
print(f"Knee Left (25): {sample_frame[25]}")
print(f"Ankle Left (27): {sample_frame[27]}")

# Transform MediaPipe (X_mp, Y_mp_down, Z_mp_depth) to Blender (X_bl, Y_bl_depth, Z_bl_up):
# X_bl = -X_mp
# Y_bl = Z_mp
# Z_bl = -Y_mp

transformed = np.zeros_like(sample_frame)
transformed[:, 0] = -sample_frame[:, 0]
transformed[:, 1] = sample_frame[:, 2]
transformed[:, 2] = -sample_frame[:, 1]

# Center hip midpoint at (0, 0, 0)
hip_mid = (transformed[23] + transformed[24]) / 2.0
transformed = transformed - hip_mid

print("\n--- Transformed Blender Coordinates ---")
print(f"Hip Center: { (transformed[23] + transformed[24]) / 2.0 }")
print(f"Shoulder Center: { (transformed[11] + transformed[12]) / 2.0 } (Z should be > 0, i.e., above hips)")
print(f"Ankle Center: { (transformed[27] + transformed[28]) / 2.0 } (Z should be < 0, i.e., below hips)")
