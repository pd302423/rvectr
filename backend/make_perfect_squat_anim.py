#!/usr/bin/env python3
"""
make_perfect_squat_anim.py

Rebuilds `videos2/squat_multiview_animated.blend` with standard relative shape keys (use_relative = True)
and individual per-frame keyframe action curves so pressing Spacebar / Play in Blender IMMEDIATELY plays the full squat animation.
"""

import os
import sys
import glob
import subprocess
import numpy as np

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
VIDEOS1_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos"))

OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

REF_OBJ_PATH = os.path.join(VIDEOS1_DIR, "squat_3d_mesh.obj")
ANCHORED_NPY_PATH = os.path.join(VIDEOS1_DIR, "squat_anchored_anim.npy")

def load_smpl_faces(ref_obj_path):
    faces = []
    with open(ref_obj_path, "r") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()
                face = [int(p.split("/")[0]) for p in parts[1:]]
                faces.append(face)
    return faces

def export_obj(verts, faces, obj_path):
    with open(obj_path, "w") as f:
        f.write("# Perfect Squat Motion SMPL 3D Human Body Surface Mesh\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

def main():
    os.makedirs(OBJ_DIR, exist_ok=True)
    faces = load_smpl_faces(REF_OBJ_PATH)

    if not os.path.exists(ANCHORED_NPY_PATH):
        print(f"[!] Error: {ANCHORED_NPY_PATH} not found.")
        sys.exit(1)

    print(f"[*] Loading squat animation dataset from {ANCHORED_NPY_PATH}...")
    verts_anim = np.load(ANCHORED_NPY_PATH) # Shape: (225, 6890, 3)
    num_frames = len(verts_anim)

    # Center stationary per-frame (COM_x, COM_z) to eliminate translation drift
    stationary_verts = np.zeros_like(verts_anim)
    for t in range(num_frames):
        v = verts_anim[t].copy()
        v[:, 0] -= np.mean(v[:, 0])
        v[:, 2] -= np.mean(v[:, 2])
        stationary_verts[t] = v

    print(f"[*] Exporting {num_frames} clean OBJ frame files to {OBJ_DIR}...")
    min_z_idx = 0
    min_z_val = 999.0

    for i in range(num_frames):
        obj_file = os.path.join(OBJ_DIR, f"frame_{i:04d}.obj")
        export_obj(stationary_verts[i], faces, obj_file)

        max_z = np.max(stationary_verts[i][:, 2])
        if max_z < min_z_val:
            min_z_val = max_z
            min_z_idx = i

    # Export peak depth single OBJ (Frame 40)
    export_obj(stationary_verts[40], faces, SINGLE_OBJ_PATH)
    print(f"[✓] Exported peak squat depth OBJ (Frame 40): {SINGLE_OBJ_PATH}")

    # Rebuild Blender project scenes
    print("[*] Rebuilding Blender .blend scenes via Blender CLI...")
    blender_script = os.path.join(VIDEOS2_DIR, "build_playable_squat.py")

    with open(blender_script, "w") as f:
        f.write("import bpy\n")
        f.write("import os\n")
        f.write("import glob\n")
        f.write("import numpy as np\n\n")

        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n")
        f.write("for m in bpy.data.meshes:\n")
        f.write("    bpy.data.meshes.remove(m)\n\n")

        f.write(f"single_obj = r'{SINGLE_OBJ_PATH}'\n")
        f.write(f"blend_out = r'{BLEND_OUT_PATH}'\n")
        f.write(f"single_blend = r'{SINGLE_BLEND_PATH}'\n")
        f.write(f"obj_dir = r'{OBJ_DIR}'\n\n")

        # Save single peak depth blend
        f.write("bpy.ops.wm.obj_import(filepath=single_obj)\n")
        f.write("if len(bpy.context.selected_objects) > 0:\n")
        f.write("    bpy.context.selected_objects[0].name = 'Squat_Actor'\n")
        f.write("bpy.ops.wm.save_as_mainfile(filepath=single_blend)\n\n")

        # Save animated blend
        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n")

        f.write("obj_files = sorted(glob.glob(os.path.join(obj_dir, '*.obj')))\n")
        f.write("bpy.ops.wm.obj_import(filepath=obj_files[0])\n")
        f.write("actor = bpy.context.selected_objects[0]\n")
        f.write("actor.name = 'Squat_Actor'\n\n")

        f.write("actor.shape_key_add(name='Basis', from_mix=False)\n")
        f.write("sk_data = actor.data.shape_keys\n")
        f.write("sk_data.use_relative = True\n\n")

        f.write("bpy.context.scene.frame_start = 1\n")
        f.write("bpy.context.scene.frame_end = len(obj_files)\n\n")

        f.write("for i, obj_p in enumerate(obj_files):\n")
        f.write("    frame_num = i + 1\n")
        f.write("    verts = []\n")
        f.write("    with open(obj_p, 'r') as ofile:\n")
        f.write("        for line in ofile:\n")
        f.write("            if line.startswith('v '):\n")
        f.write("                parts = line.strip().split()\n")
        f.write("                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])\n")
        f.write("    verts_np = np.array(verts)\n")
        f.write("    key_name = f'Frame_{frame_num:03d}' if frame_num < 1000 else f'Frame_{frame_num}'\n")
        f.write("    key = actor.shape_key_add(name=key_name, from_mix=False)\n")
        f.write("    if len(verts_np) == len(actor.data.vertices):\n")
        f.write("        for v_idx, pos in enumerate(verts_np):\n")
        f.write("            key.data[v_idx].co = pos\n")
        f.write("    key.value = 0.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num - 1)\n")
        f.write("    key.value = 1.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num)\n")
        f.write("    key.value = 0.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num + 1)\n")

        f.write("bpy.ops.wm.save_as_mainfile(filepath=blend_out)\n")

    cmd = ["blender", "-b", "--python", blender_script]
    subprocess.run(cmd, check=True)
    print("[✓] Successfully rebuilt playable squat animation scene!")

if __name__ == "__main__":
    main()
