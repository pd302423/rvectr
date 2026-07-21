import trimesh
import numpy as np
import glob
import os
import json

def calculate_angle(a, b, c):
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

out_dir = "/home/pd/Documents/rvector/backend/squat_demo_out"
obj_files = sorted(glob.glob(os.path.join(out_dir, "*.obj")))

m1 = trimesh.load(obj_files[0], process=False)
verts = m1.vertices

# 1. Find Joints
left_ankle_idx = np.where(verts[:, 0] < -0.05)[0][np.argmax(verts[verts[:, 0] < -0.05, 1])]
right_ankle_idx = np.where(verts[:, 0] > 0.05)[0][np.argmax(verts[verts[:, 0] > 0.05, 1])]

pelvis_idx = np.argmin(np.linalg.norm(verts[:, [0, 2]], axis=1))
head_idx = np.argmin(verts[:, 1])

left_knee_target = (verts[left_ankle_idx] + verts[pelvis_idx]) / 2
left_knee_target[2] -= 0.1
left_knee_idx = np.where(verts[:, 0] < -0.05)[0][np.argmin(np.linalg.norm(verts[verts[:, 0] < -0.05] - left_knee_target, axis=1))]

right_knee_target = (verts[right_ankle_idx] + verts[pelvis_idx]) / 2
right_knee_target[2] -= 0.1
right_knee_idx = np.where(verts[:, 0] > 0.05)[0][np.argmin(np.linalg.norm(verts[verts[:, 0] > 0.05] - right_knee_target, axis=1))]

left_toe_idx = np.where((verts[:, 0] < -0.05) & (verts[:, 1] > verts[left_ankle_idx, 1] - 0.05))[0][np.argmin(verts[(verts[:, 0] < -0.05) & (verts[:, 1] > verts[left_ankle_idx, 1] - 0.05), 2])]
right_toe_idx = np.where((verts[:, 0] > 0.05) & (verts[:, 1] > verts[right_ankle_idx, 1] - 0.05))[0][np.argmin(verts[(verts[:, 0] > 0.05) & (verts[:, 1] > verts[right_ankle_idx, 1] - 0.05), 2])]

left_shoulder_target = verts[head_idx].copy()
left_shoulder_target[1] += 0.3
left_shoulder_target[0] -= 0.15
left_shoulder_idx = np.argmin(np.linalg.norm(verts - left_shoulder_target, axis=1))

right_shoulder_target = verts[head_idx].copy()
right_shoulder_target[1] += 0.3
right_shoulder_target[0] += 0.15
right_shoulder_idx = np.argmin(np.linalg.norm(verts - right_shoulder_target, axis=1))


data = []
prev_depth = None

for i, f in enumerate(obj_files):
    m = trimesh.load(f, process=False)
    v = m.vertices
    
    l_hip = v[pelvis_idx].copy()
    l_hip[0] -= 0.08
    r_hip = v[pelvis_idx].copy()
    r_hip[0] += 0.08

    l_knee = v[left_knee_idx]
    l_ankle = v[left_ankle_idx]
    l_toe = v[left_toe_idx]
    
    r_knee = v[right_knee_idx]
    r_ankle = v[right_ankle_idx]
    r_toe = v[right_toe_idx]
    
    l_shoulder = v[left_shoulder_idx]
    r_shoulder = v[right_shoulder_idx]

    # Knee Flexion
    left_knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
    right_knee_angle = calculate_angle(r_hip, r_knee, r_ankle)
    
    # Hip Flexion (Shoulder - Hip - Knee)
    left_hip_angle = calculate_angle(l_shoulder, l_hip, l_knee)
    right_hip_angle = calculate_angle(r_shoulder, r_hip, r_knee)

    # Ankle Dorsiflexion (Knee - Ankle - Toe)
    left_ankle_angle = calculate_angle(l_knee, l_ankle, l_toe)
    right_ankle_angle = calculate_angle(r_knee, r_ankle, r_toe)

    # Torso Lean (Angle of Spine relative to vertical Y axis)
    spine_vector = v[head_idx] - v[pelvis_idx]
    vertical_vector = np.array([0, -1, 0])
    cosine_lean = np.dot(spine_vector, vertical_vector) / (np.linalg.norm(spine_vector) * np.linalg.norm(vertical_vector))
    torso_lean_angle = np.degrees(np.arccos(np.clip(cosine_lean, -1.0, 1.0)))

    # Squat Depth & Velocity
    squat_depth = float(v[pelvis_idx][1])
    velocity = 0.0
    if prev_depth is not None:
        velocity = (squat_depth - prev_depth) * 30.0 # meters per second (approx at 30fps)
    prev_depth = squat_depth

    knee_distance = float(np.linalg.norm(l_knee - r_knee))
    shoulder_tilt = np.degrees(np.arctan2(r_shoulder[1] - l_shoulder[1], r_shoulder[0] - l_shoulder[0]))
    
    # Segment Lengths (Body Proportions)
    l_femur = float(np.linalg.norm(l_hip - l_knee))
    r_femur = float(np.linalg.norm(r_hip - r_knee))
    l_tibia = float(np.linalg.norm(l_knee - l_ankle))
    r_tibia = float(np.linalg.norm(r_knee - r_ankle))
    torso_len = float(np.linalg.norm(v[pelvis_idx] - v[head_idx]))
    shoulder_width = float(np.linalg.norm(l_shoulder - r_shoulder))

    data.append({
        "frame": i + 1,
        "left_knee_angle": round(left_knee_angle, 2),
        "right_knee_angle": round(right_knee_angle, 2),
        "left_hip_angle": round(left_hip_angle, 2),
        "right_hip_angle": round(right_hip_angle, 2),
        "left_ankle_angle": round(left_ankle_angle, 2),
        "right_ankle_angle": round(right_ankle_angle, 2),
        "torso_lean": round(torso_lean_angle, 2),
        "shoulder_tilt": round(shoulder_tilt, 2),
        "squat_depth": round(squat_depth, 4),
        "velocity": round(velocity, 4),
        "knee_distance": round(knee_distance, 4),
        "l_femur_len": round(l_femur, 4),
        "r_femur_len": round(r_femur, 4),
        "l_tibia_len": round(l_tibia, 4),
        "r_tibia_len": round(r_tibia, 4),
        "torso_len": round(torso_len, 4),
        "shoulder_width": round(shoulder_width, 4)
    })

out_path = "/home/pd/Documents/rvector/backend/squat_kinematics.json"
with open(out_path, "w") as f:
    json.dump(data, f, indent=4)

print(f"Successfully extracted full 3D kinematics and saved to {out_path}!")
