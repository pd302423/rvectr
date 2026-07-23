#!/usr/bin/env python3
"""
enhance_muscular_anchored_smpl.py

1. Ground Anchoring & Root Stabilization:
   - Eliminates "flying around" camera translation jitter.
   - Centers subject on X=0, Y=0 and pins lowest foot vertex to ground Z=0 across all 225 frames.
   - Applies Savitzky-Golay temporal smoothing over motion trajectory.

2. Muscular Physique Surface Sculpting:
   - Applies athletic/muscular SMPL shape deformation (deltoid breadth, chest volume, latissimus V-taper, quadriceps bulk).
   - Re-exports full 6,890-vertex muscular SMPL 3D body surface meshes into `videos2/obj_sequence/` and `videos2/squat_3d_mesh.obj`.

3. Rebuilds single-actor Blender projects:
   - `videos2/squat_multiview_animated.blend` (1 muscular SMPL actor anchored to ground plane).
   - `videos2/squat_3d_mesh.blend`.
"""

import os
import sys
import glob
import subprocess
import numpy as np
import trimesh
from scipy.signal import savgol_filter

VIDEOS2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos2"))
VIDEOS1_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos"))

OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

REF_OBJ = os.path.join(VIDEOS1_DIR, "squat_3d_mesh.obj")
VERT_NPY = os.path.join(VIDEOS2_DIR, "squat_vertices_anim.npy")

def load_smpl_faces(ref_obj_path):
    faces = []
    with open(ref_obj_path, "r") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()
                face = [int(p.split("/")[0]) for p in parts[1:]]
                faces.append(face)
    return faces

def apply_muscular_physique_morph(verts):
    """
    Deforms 6,890 SMPL body vertices to reflect a muscular calisthenics athlete physique:
    - Expanded deltoids & shoulders (outer X/Z dimensions above waist)
    - Enlarged chest & latissimus (upper torso expansion)
    - Defined quadriceps & gluteal muscle volume
    """
    m_verts = verts.copy()
    com_y = np.mean(m_verts[:, 1])

    # Vertex heights relative to bounding box
    min_y, max_y = np.min(m_verts[:, 1]), np.max(m_verts[:, 1])
    height_span = max_y - min_y

    for i in range(len(m_verts)):
        x, y, z = m_verts[i]
        rel_y = (y - min_y) / height_span # 0.0 at feet, 1.0 at head

        # 1. Muscular Torso & Chest / Lats Expansion (rel_y between 0.55 and 0.85)
        if 0.55 <= rel_y <= 0.85:
            torso_factor = 1.0 + 0.14 * np.sin(np.pi * (rel_y - 0.55) / 0.30)
            m_verts[i, 0] *= torso_factor # Deltoid & shoulder width
            m_verts[i, 2] *= (1.0 + 0.12 * np.sin(np.pi * (rel_y - 0.55) / 0.30)) # Pectoral & lat thickness

        # 2. Muscular Legs & Quads Expansion (rel_y between 0.20 and 0.55)
        elif 0.20 <= rel_y < 0.55:
            leg_factor = 1.0 + 0.10 * np.sin(np.pi * (rel_y - 0.20) / 0.35)
            m_verts[i, 0] *= leg_factor
            m_verts[i, 2] *= leg_factor

        # 3. Muscular Arms (Biceps/Triceps/Forearms) (outer X regions in upper body)
        if rel_y > 0.50 and abs(x) > 0.18:
            m_verts[i, 0] *= 1.12
            m_verts[i, 2] *= 1.10

    return m_verts

def export_smpl_obj(verts, faces, obj_path):
    with open(obj_path, "w") as f:
        f.write("# Muscular SMPL 3D Human Body Surface Mesh (6,890 Vertices, 13,776 Faces)\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

def main():
    os.makedirs(OBJ_DIR, exist_ok=True)
    faces = load_smpl_faces(REF_OBJ)

    if not os.path.exists(VERT_NPY):
        print(f"[!] Error: {VERT_NPY} not found.")
        sys.exit(1)

    raw_verts = np.load(VERT_NPY) # Shape: (225, 6890, 3)
    num_frames = len(raw_verts)
    print(f"[*] Processing {num_frames} frames for Ground Anchoring & Muscular Sculpting...")

    # 1. Apply Savitzky-Golay Temporal Filter to eliminate camera translation jitter
    win_len = min(15, num_frames)
    if win_len % 2 == 0:
        win_len -= 1
    smoothed_verts = savgol_filter(raw_verts, window_length=win_len, polyorder=3, axis=0)

    # 2. Ground Anchoring (Center X=0, Z=0 & Pin Lowest Foot to Y=0 Ground)
    anchored_verts = np.zeros_like(smoothed_verts)
    for i in range(num_frames):
        v = smoothed_verts[i].copy()

        # Center of mass X and Z
        com_x = np.mean(v[:, 0])
        com_z = np.mean(v[:, 2])
        min_y = np.min(v[:, 1]) # Lowest foot contact point

        v[:, 0] -= com_x
        v[:, 2] -= com_z
        v[:, 1] -= min_y # Pin feet to ground plane Y=0

        # 3. Apply Muscular Physique Morphing
        anchored_verts[i] = apply_muscular_physique_morph(v)

    print(f"[*] Re-exporting {num_frames} muscular, ground-anchored SMPL .OBJ sequence files...")
    min_hip_idx = 0
    min_hip_y = 999.0

    for i in range(num_frames):
        obj_file = os.path.join(OBJ_DIR, f"frame_{i:04d}.obj")
        export_smpl_obj(anchored_verts[i], faces, obj_file)

        avg_y = np.mean(anchored_verts[i][:, 1])
        if avg_y < min_hip_y:
            min_hip_y = avg_y
            min_hip_idx = i

    # Export peak depth single OBJ
    export_smpl_obj(anchored_verts[min_hip_idx], faces, SINGLE_OBJ_PATH)
    print(f"[✓] Exported peak depth muscular SMPL OBJ: {SINGLE_OBJ_PATH}")

    # Save anchored muscular numpy datasets
    np.save(os.path.join(VIDEOS2_DIR, "squat_vertices_anim.npy"), anchored_verts)
    np.save(os.path.join(VIDEOS2_DIR, "squat_male_accurate_anim.npy"), anchored_verts[:, :33, :])

    # Rebuild Blender scenes using single-actor Shape Key script
    print("[*] Rebuilding Blender .blend projects with anchored muscular actor...")
    blender_script = os.path.join(VIDEOS2_DIR, "build_muscular_blend.py")
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
        f.write("    bpy.context.selected_objects[0].name = 'Muscular_SMPL_Actor'\n")
        f.write("bpy.ops.wm.save_as_mainfile(filepath=single_blend)\n\n")

        # Save animated blend
        f.write("bpy.ops.object.select_all(action='SELECT')\n")
        f.write("bpy.ops.object.delete()\n")

        f.write("obj_files = sorted(glob.glob(os.path.join(obj_dir, '*.obj')))\n")
        f.write("bpy.ops.wm.obj_import(filepath=obj_files[0])\n")
        f.write("actor = bpy.context.selected_objects[0]\n")
        f.write("actor.name = 'Muscular_SMPL_Actor'\n\n")

        f.write("actor.shape_key_add(name='Basis', from_mix=False)\n")
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
    print("[✓] Finished rebuilding anchored muscular SMPL Blender scenes!")

if __name__ == "__main__":
    main()
