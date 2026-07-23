#!/usr/bin/env python3
"""
export_obj_and_blend.py

Exports `.obj` sequence files and `.blend` Blender files for `videos2`
using the recalibrated 3D motion keypoint data (`videos2/squat_multiview_anim.npy`).
"""

import os
import sys
import glob
import subprocess
import numpy as np

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
ANIM_NPY_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy")
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUTPUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

# MediaPipe 33 Landmark Connections for 3D Skeleton Mesh
CONNECTIONS = [
  (11, 12), (11, 23), (12, 24), (23, 24), # Torso
  (11, 13), (13, 15), # Left Arm
  (12, 14), (14, 16), # Right Arm
  (23, 25), (25, 27), (27, 29), (29, 31), (27, 31), # Left Leg
  (24, 26), (26, 28), (28, 30), (30, 32), (28, 32), # Right Leg
  (0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6)   # Head / Face
]

def generate_obj_file_for_frame(joints3d: np.ndarray, obj_path: str, radius=0.04):
    """Generates Wavefront OBJ mesh file with joint spheres and bone cylinder connectors."""
    vertices = []
    faces = []

    # Create joint spheres (icosahedron approximation)
    for j_idx, pt in enumerate(joints3d):
        base_v = len(vertices) + 1
        x, y, z = pt[0], pt[1], pt[2]

        # 12-vertex icosahedron for each joint node
        phi = (1.0 + np.sqrt(5.0)) / 2.0
        ico_verts = np.array([
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
        ]) * radius + np.array([x, y, z])

        ico_faces = [
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
        ]

        for v in ico_verts:
            vertices.append(v)
        for f in ico_faces:
            faces.append([base_v + f[0], base_v + f[1], base_v + f[2]])

    # Create bone cylinders between connected joint pairs
    for p1_idx, p2_idx in CONNECTIONS:
        if p1_idx >= len(joints3d) or p2_idx >= len(joints3d):
            continue

        p1 = joints3d[p1_idx]
        p2 = joints3d[p2_idx]

        # Simple line/cylinder segment between p1 and p2
        v_base = len(vertices) + 1
        vertices.append(p1)
        vertices.append(p2)
        vertices.append(p1 + np.array([0, 0.01, 0]))
        faces.append([v_base, v_base + 1, v_base + 2])

    with open(obj_path, "w") as f:
        f.write("# Wavefront OBJ created by rvector biomechanics engine\n")
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

def export_objs_and_blender():
    os.makedirs(OBJ_DIR, exist_ok=True)

    if not os.path.exists(ANIM_NPY_PATH):
        print(f"[!] Error: {ANIM_NPY_PATH} not found.")
        sys.exit(1)

    motion_3d = np.load(ANIM_NPY_PATH)
    num_frames = len(motion_3d)
    print(f"[*] Generating {num_frames} Wavefront .OBJ sequence files in {OBJ_DIR}...")

    # Find peak squat depth frame (lowest Y position of hips/knees)
    min_y_frame = 0
    min_y_val = 999.0

    for i in range(num_frames):
        obj_filename = f"frame_{i:04d}.obj"
        obj_path = os.path.join(OBJ_DIR, obj_filename)
        generate_obj_file_for_frame(motion_3d[i], obj_path)

        # Peak depth check (joint 23 & 24 hips Y coordinate)
        hip_y = (motion_3d[i][23][1] + motion_3d[i][24][1]) / 2.0
        if hip_y < min_y_val:
            min_y_val = hip_y
            min_y_frame = i

    # Export peak depth single .obj file
    generate_obj_file_for_frame(motion_3d[min_y_frame], SINGLE_OBJ_PATH, radius=0.05)
    print(f"[✓] Saved peak depth single .OBJ file: {SINGLE_OBJ_PATH} (frame {min_y_frame})")

    # Generate Blender Python script to import OBJ sequence and save .blend file
    blender_script_path = os.path.join(VIDEOS2_DIR, "import_objs.py")
    blender_script_content = f"""import bpy
import os
import glob

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

obj_dir = r"{OBJ_DIR}"
blend_out = r"{BLEND_OUTPUT_PATH}"
single_out = r"{SINGLE_BLEND_PATH}"

obj_files = sorted(glob.glob(os.path.join(obj_dir, "*.obj")))
print(f"[*] Blender importing {{len(obj_files)}} .obj files...")

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(obj_files)

for i, obj_path in enumerate(obj_files):
    frame_num = i + 1
    bpy.ops.object.select_all(action='DESELECT')
    try:
        bpy.ops.wm.obj_import(filepath=obj_path)
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=obj_path)

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

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print(f"[✓] Saved animated Blender file to {{blend_out}}")

# Save single blend file
bpy.ops.wm.save_as_mainfile(filepath=single_out)
print(f"[✓] Saved single Blender file to {{single_out}}")
"""
    with open(blender_script_path, "w") as f:
        f.write(blender_script_content)

    print(f"[*] Invoking Blender CLI to build .blend files...")
    cmd = ["blender", "-b", "--python", blender_script_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"[✓] Successfully exported:")
    print(f"    - {BLEND_OUTPUT_PATH}")
    print(f"    - {SINGLE_BLEND_PATH}")
    print(f"    - {SINGLE_OBJ_PATH}")
    print(f"    - {OBJ_DIR} ({num_frames} .obj files)")

if __name__ == "__main__":
    export_objs_and_blender()
