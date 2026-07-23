#!/usr/bin/env python3
"""
build_single_actor_blend.py

Builds a clean, single-actor Blender project (`videos2/squat_multiview_animated.blend`)
using Shape Key animation on ONE single mesh object ('Squat_Actor') — replacing 557 jumbled OBJ objects with 1 clean animated actor!
"""

import os
import sys
import glob
import subprocess
import numpy as np

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

def main():
    blender_builder_script = os.path.join(VIDEOS2_DIR, "build_shapekey_actor.py")

    with open(blender_builder_script, "w") as f:
        f.write("import bpy\n")
        f.write("import os\n")
        f.write("import glob\n")
        f.write("import numpy as np\n")
        f.write("import sys\n\n")

        f.write("print('[*] Starting Single-Actor Shape Key Blender construction...')\n\n")
        f.write("# 1. Clean scene\n")
        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n")
        f.write("for m in bpy.data.meshes:\n")
        f.write("    bpy.data.meshes.remove(m)\n\n")

        f.write(f"single_obj_path = r'{SINGLE_OBJ_PATH}'\n")
        f.write(f"blend_out_path = r'{BLEND_OUT_PATH}'\n")
        f.write(f"single_blend_path = r'{SINGLE_BLEND_PATH}'\n")
        f.write(f"obj_dir = r'{OBJ_DIR}'\n\n")

        f.write("# 2. Build Single Peak Depth .blend\n")
        f.write("bpy.ops.wm.obj_import(filepath=single_obj_path)\n")
        f.write("imported_objs = bpy.context.selected_objects\n")
        f.write("if len(imported_objs) > 0:\n")
        f.write("    single_actor = imported_objs[0]\n")
        f.write("    single_actor.name = 'Squat_Actor'\n")
        f.write("bpy.ops.wm.save_as_mainfile(filepath=single_blend_path)\n")
        f.write("print(f'[✓] Saved single peak depth blend to {single_blend_path}')\n\n")

        f.write("# 3. Build Animated Single-Actor .blend using Shape Keys\n")
        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n\n")

        f.write("obj_files = sorted(glob.glob(os.path.join(obj_dir, '*.obj')))\n")
        f.write("if len(obj_files) == 0:\n")
        f.write("    print('[!] Error: No obj files found in obj_sequence')\n")
        f.write("    sys.exit(1)\n\n")

        f.write("print(f'[*] Loading {len(obj_files)} frame meshes into ONE single actor object...')\n\n")

        f.write("# Import frame 0 to create the primary actor mesh\n")
        f.write("bpy.ops.wm.obj_import(filepath=obj_files[0])\n")
        f.write("actor = bpy.context.selected_objects[0]\n")
        f.write("actor.name = 'Squat_Actor'\n\n")

        f.write("# Add Basis Shape Key\n")
        f.write("actor.shape_key_add(name='Basis', from_mix=False)\n")
        f.write("bpy.context.scene.frame_start = 1\n")
        f.write("bpy.context.scene.frame_end = len(obj_files)\n\n")

        f.write("# Parse vertices for each frame OBJ file and add Shape Keys\n")
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
        f.write("            key.data[v_idx].co = pos\n")
        f.write("    key.value = 0.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num - 1)\n")
        f.write("    key.value = 1.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num)\n")
        f.write("    key.value = 0.0\n")
        f.write("    key.keyframe_insert(data_path='value', frame=frame_num + 1)\n")
        f.write("    if i % 100 == 0:\n")
        f.write("        print(f'  Processed frame {frame_num}/{len(obj_files)}...')\n\n")

        f.write("bpy.ops.wm.save_as_mainfile(filepath=blend_out_path)\n")
        f.write("print(f'[✓] Successfully saved Single-Actor animated scene to {blend_out_path} with 1 actor object!')\n")

    print("[*] Running Blender CLI to generate single-actor .blend files...")
    cmd = ["blender", "-b", "--python", blender_builder_script]
    subprocess.run(cmd, check=True)
    print("[✓] Finished building single-actor Blender project!")

if __name__ == "__main__":
    main()
