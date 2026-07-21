import trimesh
import numpy as np
import glob
import os
from scipy.signal import savgol_filter

out_dir = "/home/pd/Documents/rvector/backend/squat_demo_out"
obj_files = sorted(glob.glob(os.path.join(out_dir, "*.obj")))

meshes = []
all_verts = []
for f in obj_files:
    m = trimesh.load(f, process=False)
    meshes.append(m)
    all_verts.append(m.vertices)

all_verts = np.array(all_verts)

print("Applying mathematical smoothing to EVERY vertex to eliminate all pose jitter...")
# This completely smooths out all shaking/jittering in the arms, legs, and body!
smoothed_verts = savgol_filter(all_verts, window_length=15, polyorder=3, axis=0)

print("Pinning the character perfectly to the center of the world...")
# Calculate the center of mass for the newly smoothed meshes
com = smoothed_verts.mean(axis=1) # Shape: (161, 3)

# Pin the character exactly to X=0 and Z=0 on every frame to eliminate back-and-forth drifting
smoothed_verts[:, :, 0] -= com[:, 0, None]
smoothed_verts[:, :, 2] -= com[:, 2, None]

# We DO NOT subtract anything from Y! We leave Y alone so the squat motion stays intact.

print("Saving final perfect meshes...")
for i, f in enumerate(obj_files):
    meshes[i].vertices = smoothed_verts[i]
    meshes[i].export(f)
print("Done!")
