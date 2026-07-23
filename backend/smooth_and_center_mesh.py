import os
import glob
import numpy as np
import trimesh
from scipy.signal import savgol_filter

def smooth_and_center(obj_dir, out_dir, window_length=15, polyorder=3):
    os.makedirs(out_dir, exist_ok=True)
    obj_files = sorted(glob.glob(os.path.join(obj_dir, "*.obj")))
    num_files = len(obj_files)
    print(f"[*] Found {num_files} OBJ files in {obj_dir}")

    if num_files == 0:
        print("[!] No OBJ files found.")
        return

    # Load all meshes into array (num_frames, num_vertices, 3)
    meshes = []
    all_verts = []
    print("[*] Loading mesh vertices for temporal smoothing...")
    for f in obj_files:
        m = trimesh.load(f, process=False)
        meshes.append(m)
        all_verts.append(m.vertices)

    all_verts = np.array(all_verts) # Shape: (N_frames, 6890, 3)

    # Make window length odd and <= num_files
    win_len = min(window_length, num_files)
    if win_len % 2 == 0:
        win_len -= 1
    win_len = max(3, win_len)

    print(f"[*] Applying Savitzky-Golay temporal filter (window_length={win_len}, polyorder={polyorder})...")
    # Smooth over frame axis (axis=0)
    smoothed_verts = savgol_filter(all_verts, window_length=win_len, polyorder=polyorder, axis=0)

    print("[*] Centering character to world origin (X=0, Z=0) across all frames...")
    # Calculate center of mass across vertices per frame
    com = smoothed_verts.mean(axis=1) # Shape: (N_frames, 3)

    # Pin character to center (X=0, Z=0) on every frame to remove back-and-forth drift and camera displacement
    smoothed_verts[:, :, 0] -= com[:, 0, None]
    smoothed_verts[:, :, 2] -= com[:, 2, None]

    # Save smoothed and centered meshes
    print(f"[*] Exporting smoothed and centered OBJs to {out_dir}...")
    for i, f in enumerate(obj_files):
        filename = os.path.basename(f)
        out_filepath = os.path.join(out_dir, filename)
        meshes[i].vertices = smoothed_verts[i]
        meshes[i].export(out_filepath)

    print(f"[✓] Successfully smoothed and centered {num_files} frame meshes!")

    # Export primary smoothed GLB
    first_obj = os.path.join(out_dir, os.path.basename(obj_files[0]))
    if os.path.exists(first_obj):
        glb_path = os.path.join(os.path.dirname(out_dir), "3d_mesh_model_centered.glb")
        trimesh.load(first_obj).export(glb_path)
        print(f"[✓] Exported centered 3D GLB model to {glb_path}")

if __name__ == "__main__":
    obj_in = "/home/pd/Downloads/20260723_121036_3d_mesh/obj_sequence"
    obj_out = "/home/pd/Downloads/20260723_121036_3d_mesh/obj_sequence_smoothed"
    smooth_and_center(obj_in, obj_out)
