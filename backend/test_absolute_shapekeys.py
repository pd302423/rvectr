#!/usr/bin/env python3
"""
test_absolute_shapekeys.py

Builds Absolute Shape Keys (use_relative = False) in Blender where shape keys
directly define exact vertex positions without additive deformation or warping.
"""

import os
import sys
import glob
import subprocess

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

def main():
    script_path = os.path.join(VIDEOS2_DIR, "build_absolute_shapekeys.py")

    with open(script_path, "w") as f:
        f.write("import bpy\n")
        f.write("import os\n")
        f.write("import glob\n")
        f.write("import numpy as np\n")
        f.write("import sys\n\n")

        f.write("print('[*] Building Absolute Shape Keys (use_relative=False) single-actor scene...')\n\n")
        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n")
        f.write("for m in bpy.data.meshes:\n")
        f.write("    bpy.data.meshes.remove(m)\n\n")

        f.write(f"single_obj = r'{SINGLE_OBJ_PATH}'\n")
        f.write(f"blend_out = r'{BLEND_OUT_PATH}'\n")
        f.write(f"single_blend = r'{SINGLE_BLEND_PATH}'\n")
        f.write(f"obj_dir = r'{OBJ_DIR}'\n\n")

        f.write("bpy.ops.wm.obj_import(filepath=single_obj)\n")
        f.write("if len(bpy.context.selected_objects) > 0:\n")
        f.write("    bpy.context.selected_objects[0].name = 'SMPL_Actor'\n")
        f.write("bpy.ops.wm.save_as_mainfile(filepath=single_blend)\n\n")

        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n\n")

        f.write("obj_files = sorted(glob.glob(os.path.join(obj_dir, '*.obj')))\n")
        f.write("bpy.ops.wm.obj_import(filepath=obj_files[0])\n")
        f.write("actor = bpy.context.selected_objects[0]\n")
        f.write("actor.name = 'SMPL_Actor'\n\n")

        f.write("actor.shape_key_add(name='Basis', from_mix=False)\n")
        f.write("sk_data = actor.data.shape_keys\n")
        f.write("sk_data.use_relative = False\n\n")

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
        f.write("    key_name = f'Frame_{frame_num:04d}'\n")
        f.write("    key = actor.shape_key_add(name=key_name, from_mix=False)\n")
        f.write("    if len(verts_np) == len(actor.data.vertices):\n")
        f.write("        for v_idx, pos in enumerate(verts_np):\n")
        f.write("            key.data[v_idx].co = pos\n\n")

        f.write("sk_data.eval_time = 0.0\n")
        f.write("sk_data.keyframe_insert(data_path='eval_time', frame=1)\n")
        f.write("for i in range(1, len(obj_files)):\n")
        f.write("    frame_num = i + 1\n")
        f.write("    sk_data.eval_time = float(i * 10)\n")
        f.write("    sk_data.keyframe_insert(data_path='eval_time', frame=frame_num)\n\n")

        f.write("bpy.ops.wm.save_as_mainfile(filepath=blend_out)\n")
        f.write("print(f'[✓] Successfully saved Absolute Shape Keys scene to {blend_out}!')\n")

    cmd = ["blender", "-b", "--python", script_path]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
