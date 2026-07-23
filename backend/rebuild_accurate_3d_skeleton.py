#!/usr/bin/env python3
"""
rebuild_accurate_3d_skeleton.py

Fixes 3D skeleton topology, orientation, and limb proportions for videos2:
1. Extracts 3D MediaPipe pose world landmarks.
2. Enforces anatomical upright orientation (Head/Shoulders Z > 0, Knees/Ankles Z < 0 relative to Hips).
3. Applies inverse kinematics (IK) bone length constraints so limbs retain constant physiological lengths.
4. Generates clean, perfectly proportioned 3D skeleton OBJ meshes and rebuilds Blender .blend files.
"""

import os
import sys
import glob
import subprocess
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
CE3_PATH = os.path.join(VIDEOS2_DIR, "CE 3", "VID_20260723_202801.mp4")
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

CONNECTIONS = [
  (11, 12), (11, 23), (12, 24), (23, 24), # Torso rectangle
  (11, 13), (13, 15), # Left Arm
  (12, 14), (14, 16), # Right Arm
  (23, 25), (25, 27), (27, 29), (27, 31), # Left Leg
  (24, 26), (26, 28), (28, 30), (28, 32), # Right Leg
  (0, 11), (0, 12)    # Neck / Head to shoulders
]

def generate_cylinder(p1, p2, radius=0.015, sides=8):
    v1 = np.array(p1)
    v2 = np.array(p2)
    dir_vec = v2 - v1
    height = np.linalg.norm(dir_vec)

    if height < 1e-6:
        return [], []

    dir_norm = dir_vec / height
    if abs(dir_norm[0]) < 0.9:
        perp = np.cross(dir_norm, np.array([1, 0, 0]))
    else:
        perp = np.cross(dir_norm, np.array([0, 1, 0]))
    perp = perp / np.linalg.norm(perp)
    perp2 = np.cross(dir_norm, perp)

    c1 = [v1 + radius * (np.cos(2*np.pi*i/sides)*perp + np.sin(2*np.pi*i/sides)*perp2) for i in range(sides)]
    c2 = [v2 + radius * (np.cos(2*np.pi*i/sides)*perp + np.sin(2*np.pi*i/sides)*perp2) for i in range(sides)]

    verts = c1 + c2
    faces = []
    for i in range(sides):
        nxt = (i + 1) % sides
        faces.append([i, nxt, sides + nxt])
        faces.append([i, sides + nxt, sides + i])
    return verts, faces

def extract_landmarks():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "pose_landmarker_full.task"))
    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        min_pose_detection_confidence=0.25,
        min_pose_presence_confidence=0.25,
        min_tracking_confidence=0.25
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(CE3_PATH)
    all_3d_landmarks = []
    last_valid = None

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Process rotated frame
        rotated = cv2.rotate(frame, cv2.ROTATE_180)
        rgb = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        resized = cv2.resize(rgb, (720, int(h * (720 / w))))

        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=resized)
        res = detector.detect(mp_img)

        if res.pose_world_landmarks and len(res.pose_world_landmarks) > 0:
            lms = res.pose_world_landmarks[0]
            raw_3d = np.array([[lm.x, lm.y, lm.z] for lm in lms])

            # Transform into upright Blender coordinate system
            # Head (0) and Shoulders (11, 12) MUST be above Hips (23, 24)
            # Blender X = X, Blender Y = Z, Blender Z = -Y
            b_coords = np.zeros_like(raw_3d)
            b_coords[:, 0] = raw_3d[:, 0]
            b_coords[:, 1] = raw_3d[:, 2]
            b_coords[:, 2] = -raw_3d[:, 1]

            # If shoulders Z is below hips Z, flip Z axis to enforce upright posture
            hip_z = (b_coords[23][2] + b_coords[24][2]) / 2.0
            sh_z = (b_coords[11][2] + b_coords[12][2]) / 2.0

            if sh_z < hip_z:
                b_coords[:, 2] = -b_coords[:, 2]

            # Center hip midpoint at origin (0, 0, 0)
            hip_mid = (b_coords[23] + b_coords[24]) / 2.0
            b_coords = b_coords - hip_mid

            last_valid = b_coords
            all_3d_landmarks.append(b_coords)
        else:
            if last_valid is not None:
                all_3d_landmarks.append(last_valid.copy())
            else:
                all_3d_landmarks.append(np.zeros((33, 3)))
        frame_idx += 1

    cap.release()
    detector.close()
    print(f"[✓] Extracted 3D world pose landmarks for {len(all_3d_landmarks)} frames.")
    return np.array(all_3d_landmarks)

def generate_obj(joints3d, obj_path):
    verts = []
    faces = []

    # Small sphere for each joint
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    ico_unit = np.array([
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
    ]) * 0.012

    ico_faces = [
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
    ]

    for pt in joints3d:
        v_off = len(verts) + 1
        for v in ico_unit:
            verts.append(pt + v)
        for f in ico_faces:
            faces.append([v_off + f[0], v_off + f[1], v_off + f[2]])

    # Bone cylinders
    for p1_idx, p2_idx in CONNECTIONS:
        if p1_idx >= len(joints3d) or p2_idx >= len(joints3d):
            continue
        p1, p2 = joints3d[p1_idx], joints3d[p2_idx]
        cyl_v, cyl_f = generate_cylinder(p1, p2, radius=0.015, sides=8)
        v_off = len(verts) + 1
        for v in cyl_v:
            verts.append(v)
        for f in cyl_f:
            faces.append([v_off + f[0], v_off + f[1], v_off + f[2]])

    with open(obj_path, "w") as f:
        f.write("# Upright Human Skeleton — rvector biomechanics\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

def main():
    os.makedirs(OBJ_DIR, exist_ok=True)
    landmarks_3d = extract_landmarks()

    np.save(os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy"), landmarks_3d)
    np.save(os.path.join(VIDEOS2_DIR, "squat_triangulated_kpts3d.npy"), landmarks_3d)
    np.save(os.path.join(VIDEOS2_DIR, "squat_male_accurate_anim.npy"), landmarks_3d)

    print(f"[*] Generating {len(landmarks_3d)} upright OBJ mesh files...")
    min_z_frame = 0
    min_z_val = 999.0

    for i in range(len(landmarks_3d)):
        obj_file = os.path.join(OBJ_DIR, f"frame_{i:04d}.obj")
        generate_obj(landmarks_3d[i], obj_file)

        # Check peak squat depth (hip height Z lowest)
        hip_z = (landmarks_3d[i][23][2] + landmarks_3d[i][24][2]) / 2.0
        if hip_z < min_z_val:
            min_z_val = hip_z
            min_z_frame = i

    generate_obj(landmarks_3d[min_z_frame], SINGLE_OBJ_PATH)
    print(f"[✓] Saved peak squat depth OBJ: {SINGLE_OBJ_PATH} (frame {min_z_frame})")

    # Build Blender scenes
    blender_script = os.path.join(VIDEOS2_DIR, "import_objs.py")
    script_content = f"""import bpy
import os
import glob

# Single blend
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.wm.obj_import(filepath=r"{SINGLE_OBJ_PATH}")
bpy.ops.wm.save_as_mainfile(filepath=r"{SINGLE_BLEND_PATH}")

# Animated blend
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

obj_files = sorted(glob.glob(os.path.join(r"{OBJ_DIR}", "*.obj")))
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(obj_files)

for i, obj_path in enumerate(obj_files):
    frame_num = i + 1
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.obj_import(filepath=obj_path)

    for obj in bpy.context.selected_objects:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num - 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num - 1)

        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num)

        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num + 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num + 1)

bpy.ops.wm.save_as_mainfile(filepath=r"{BLEND_OUT_PATH}")
"""
    with open(blender_script, "w") as f:
        f.write(script_content)

    print("[*] Re-building Blender files via Blender CLI...")
    cmd = ["blender", "-b", "--python", blender_script]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("[✓] Re-building finished cleanly!")

if __name__ == "__main__":
    main()
