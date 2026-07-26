#!/usr/bin/env python3
"""
run_easymocap_videos2.py

!!! WARNING — THIS SCRIPT DOES NOT PRODUCE MOTION CAPTURE OUTPUT. !!!

Steps 1 and 2 do real work. Step 3 THROWS IT AWAY and substitutes a
hand-authored sine-wave animation. Everything downstream (OBJ, NPY, BLEND,
GLB) is therefore SYNTHETIC and must never be presented as a capture result.

1. REAL — Calibrates camera intrinsics & extrinsics (CE 3 + Nord) from
   chessboard targets. Falls back to *estimated* 4K lens parameters if
   chessboard detection fails, which is itself unvalidated.
2. REAL — Extracts multi-view 2D pose keypoints with MediaPipe, writes
   per-frame annotations to `annots/`.
3. FAKE — `synthesize_scripted_squat_smpl()` ignores the keypoints from
   step 2 entirely. No triangulation. No SMPL fitting. It writes hardcoded
   joint angles (`raw_poses[f, 12] = 1.45 * progress`, etc.) into a 72-param
   pose vector driven by `sin(pi * t)`, then smooths them.
4-6. Exports the synthetic animation to OBJ / NPY / BLEND / GLB.

TO MAKE THIS A REAL PIPELINE, step 3 must be replaced with actual EasyMocap
triangulation + fitting against the step-2 keypoints. Until then, treat this
as an authored-animation generator.
"""

import os
import sys
import glob
import json
import shutil
import subprocess
import cv2
import numpy as np
import torch
from scipy.signal import savgol_filter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS2_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "videos2"))
EASYMOCAP_DIR = os.path.join(SCRIPT_DIR, "EasyMocap")
sys.path.append(EASYMOCAP_DIR)

from easymocap.mytools.camera_utils import write_camera

# Inputs
CE3_SQUAT = os.path.join(VIDEOS2_DIR, "CE 3", "VID_20260723_202801.mp4")
NORD_SQUAT = os.path.join(VIDEOS2_DIR, "Nord", "VID_20260723_202801.mp4")
CE3_CALIB = os.path.join(VIDEOS2_DIR, "CE 3", "IMG_20260723_204341.jpg")
NORD_CALIB = os.path.join(VIDEOS2_DIR, "Nord", "IMG_20260723_203511.jpg")

# Outputs
DATASET_DIR = os.path.join(VIDEOS2_DIR, "easymocap_dataset")
SQUAT_PATH = os.path.join(DATASET_DIR, "squat")
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")
GLB_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.glb")
SINGLE_GLB_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.glb")

def calibrate_cameras():
    """Calibrates camera intrinsics & extrinsics for CE 3 (01) and Nord (02) using chessboard patterns."""
    print("[*] Step 1: Calibrating camera intrinsics & extrinsics from chessboard calibration images...")
    os.makedirs(SQUAT_PATH, exist_ok=True)
    
    img1 = cv2.imread(CE3_CALIB)
    img2 = cv2.imread(NORD_CALIB)
    
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    
    # Detect chessboard corners
    ret1, corners1 = cv2.findChessboardCorners(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), (9, 6))
    ret2, corners2 = cv2.findChessboardCorners(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY), (9, 7))
    
    if not ret1 or not ret2:
        print("[!] Warning: Chessboard detection fallback using estimated 4K lens parameters...")
        K1 = np.array([[2840.0, 0.0, w1 / 2.0], [0.0, 2840.0, h1 / 2.0], [0.0, 0.0, 1.0]])
        K2 = np.array([[2840.0, 0.0, w2 / 2.0], [0.0, 2840.0, h2 / 2.0], [0.0, 0.0, 1.0]])
        R1, T1 = np.eye(3), np.zeros((3, 1))
        R2, T2 = np.eye(3), np.array([[0.5], [0.0], [0.1]])
        dist1, dist2 = np.zeros((1, 5)), np.zeros((1, 5))
    else:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        cv2.cornerSubPix(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), corners1, (11, 11), (-1, -1), criteria)
        cv2.cornerSubPix(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY), corners2, (11, 11), (-1, -1), criteria)
        
        # Camera 1 (01) intrinsic
        objp1 = np.zeros((9 * 6, 3), np.float32)
        objp1[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2) * 0.05
        ret1, K1, dist1, rvecs1, tvecs1 = cv2.calibrateCamera([objp1], [corners1], (w1, h1), None, None)
        
        # Camera 2 (02) intrinsic
        objp2 = np.zeros((9 * 7, 3), np.float32)
        objp2[:, :2] = np.mgrid[0:9, 0:7].T.reshape(-1, 2) * 0.05
        ret2, K2, dist2, rvecs2, tvecs2 = cv2.calibrateCamera([objp2], [corners2], (w2, h2), None, None)
        
        R1, _ = cv2.Rodrigues(rvecs1[0])
        T1 = tvecs1[0].reshape(3, 1)
        R2, _ = cv2.Rodrigues(rvecs2[0])
        T2 = tvecs2[0].reshape(3, 1)

    cam_data = {
        '01': {'K': K1, 'dist': dist1, 'R': R1, 'T': T1},
        '02': {'K': K2, 'dist': dist2, 'R': R2, 'T': T2}
    }
    write_camera(cam_data, SQUAT_PATH)
    print(f"[✓] Created intri.yml & extri.yml calibration matrices using EasyMocap schema!")

def extract_2d_keypoints():
    """Extracts 2D pose keypoints across multi-view videos."""
    print("[*] Step 2: Extracting 2D pose keypoints for Camera 01 (CE 3) and Camera 02 (Nord)...")
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    
    model_path = os.path.join(SCRIPT_DIR, "pose_landmarker_full.task")
    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3
    )
    
    for cam_id, video_path in [("01", CE3_SQUAT), ("02", NORD_SQUAT)]:
        detector = vision.PoseLandmarker.create_from_options(options)
        annot_dir = os.path.join(SQUAT_PATH, "annots", cam_id)
        os.makedirs(annot_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            rotated = cv2.rotate(frame, cv2.ROTATE_180)
            rgb = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
            
            target_w = 720
            target_h = int(h * (target_w / w))
            resized_rgb = cv2.resize(rgb, (target_w, target_h))
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=resized_rgb)
            results = detector.detect(mp_image)
            
            kpts2d = np.zeros((25, 3))
            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                lms = results.pose_landmarks[0]
                for i, lm in enumerate(lms[:25]):
                    kpts2d[i] = [lm.x * w, lm.y * h, getattr(lm, "visibility", 1.0)]
            
            annot_json = os.path.join(annot_dir, f"{frame_idx:06d}.json")
            with open(annot_json, "w") as f:
                json.dump({"people": [{"pose_keypoints_2d": kpts2d.flatten().tolist()}]}, f)
            frame_idx += 1
            
        cap.release()
        detector.close()
        print(f"[✓] Saved 2D keypoint annotations for Cam {cam_id} ({frame_idx} frames)")

def synthesize_scripted_squat_smpl():
    """
    !!! THIS DOES NOT PERFORM MOTION CAPTURE. !!!

    Generates a HAND-AUTHORED squat animation from a hardcoded sine wave. The
    output SMPL mesh sequence is SYNTHETIC and has NO relationship to the
    recorded video beyond borrowing its frame count.

    Specifically: the dataset and body model are loaded, but `dataset` is used
    ONLY for `len(dataset)`. No 2D keypoints are read, no triangulation is
    performed, and no fitting occurs. Every joint angle below is a literal
    authored by hand (e.g. `raw_poses[f, 12] = 1.45 * progress` for left knee).

    This function was previously named `fit_easymocap_3d_smpl` and announced
    itself as "EasyMocap multi-view 3D triangulation & SMPL fitting". Any mesh,
    GLB, OBJ, or kinematics file produced through it is an animation, NOT a
    measurement, and must never be presented as a capture result.

    RETAINED because authored-pose synthesis is exactly what the ground-truth
    harness needs (see docs/RESEARCH_ROADMAP.md) — a known theta, rendered.
    To become that harness it needs: the authored theta persisted alongside the
    mesh, and a real recovery path to compare against. Until then it produces
    ground truth with nothing measured against it.
    """
    print("[!] Step 3: SYNTHESIZING a scripted squat animation from hardcoded joint")
    print("[!]         angles. THIS IS NOT MOTION CAPTURE. No triangulation or SMPL")
    print("[!]         fitting is performed. Output is an authored animation.")
    from easymocap.smplmodel import load_model
    from easymocap.dataset import CONFIG, MV1PMF
    
    out_dir = os.path.join(SQUAT_PATH, "output")
    os.makedirs(out_dir, exist_ok=True)
    
    model_dir = os.path.join(EASYMOCAP_DIR, "data", "smplx")
    smpl_sub = os.path.join(model_dir, "smpl")
    smplx_sub = os.path.join(model_dir, "smplx")
    os.makedirs(smpl_sub, exist_ok=True)
    os.makedirs(smplx_sub, exist_ok=True)
    
    for f in ['SMPL_NEUTRAL.pkl', 'SMPL_MALE.pkl', 'SMPL_FEMALE.pkl', 'SMPL_NEUTRAL.npz', 'SMPL_MALE.npz', 'SMPL_FEMALE.npz']:
        src = os.path.join(model_dir, f)
        dst_s = os.path.join(smpl_sub, f)
        dst_sx = os.path.join(smplx_sub, f.replace('SMPL', 'SMPLX'))
        if os.path.exists(src):
            if not os.path.exists(dst_s): os.symlink(src, dst_s)
            if not os.path.exists(dst_sx): os.symlink(src, dst_sx)
            
    dataset = MV1PMF(SQUAT_PATH, annot_root=os.path.join(SQUAT_PATH, "annots"), cams=["01", "02"], out=out_dir, config=CONFIG["smpl"], kpts_type="smpl", undis=False, no_img=True, verbose=False)
    
    body_model = load_model(gender="neutral", model_type="smpl", model_path=model_dir)
    
    print("[!] Writing hardcoded joint angles into a 72-param SMPL pose vector (authored, not fitted)...")
    num_frames = len(dataset)
    
    raw_poses = np.zeros((num_frames, 72))
    
    for f in range(num_frames):
        t = f / max(1, num_frames - 1)
        progress = np.sin(np.pi * t)
        
        # Lower body squat flexions
        raw_poses[f, 3] = -0.95 * progress   # Left Hip
        raw_poses[f, 6] = -0.95 * progress   # Right Hip
        raw_poses[f, 12] = 1.45 * progress   # Left Knee
        raw_poses[f, 15] = 1.45 * progress   # Right Knee
        raw_poses[f, 21] = -0.45 * progress  # Left Ankle
        raw_poses[f, 24] = -0.45 * progress  # Right Ankle
        raw_poses[f, 9] = 0.35 * progress    # Spine
        
        # Upper body & shoulders
        raw_poses[f, 48] = -0.35 * progress   # Left Shoulder pitch
        raw_poses[f, 49] = -0.20 * progress   # Left Shoulder yaw
        raw_poses[f, 50] = -0.65              # Left Shoulder roll
        
        raw_poses[f, 51] = -0.35 * progress   # Right Shoulder pitch
        raw_poses[f, 52] = 0.20 * progress    # Right Shoulder yaw
        raw_poses[f, 53] = 0.65               # Right Shoulder roll
        
        # INVERTED ELBOW FLEXION: Flex forearms UPWARDS in front of chest & face
        raw_poses[f, 55] = -0.75 * progress   # Left Elbow inverted (UPWARDS)
        raw_poses[f, 58] = 0.75 * progress    # Right Elbow inverted (UPWARDS)

    # Savitzky-Golay, NOT Gaussian. A Gaussian filter attenuates local extrema,
    # and peak joint angles (max knee flexion, max hip flexion) are exactly the
    # quantities this project measures. Attenuation worsens as movement speeds
    # up, which would manufacture a velocity-dependent error trend even from a
    # perfect estimator. Savitzky-Golay fits a local polynomial and preserves
    # peak amplitude far better at comparable noise rejection.
    # Window must be odd and <= number of frames.
    win_len = min(15, num_frames if num_frames % 2 == 1 else num_frames - 1)
    if win_len >= 5:
        smoothed_poses = savgol_filter(raw_poses, window_length=win_len, polyorder=3, axis=0)
    else:
        smoothed_poses = raw_poses  # too few frames to filter meaningfully

    # NOTE: these are axis-angle rotation parameters. Filtering axis-angle
    # component-wise is not rotation-correct (it ignores the manifold and can
    # misbehave near pi). The roadmap specifies `roma` for rotation handling;
    # this should convert to a continuous representation before filtering.
    
    all_smpl_vertices = []
    for f in range(num_frames):
        t = f / max(1, num_frames - 1)
        progress = np.sin(np.pi * t)
        
        params = {
            'poses': smoothed_poses[f:f+1],
            'shapes': np.zeros((1, 10)),
            'Rh': np.zeros((1, 3)),
            'Th': np.array([[0.0, -0.40 * progress, 0.0]])
        }
        
        verts = body_model(return_verts=True, return_tensor=False, **params)[0]
        
        # Convert SMPL (Y-up, Z-forward) directly to Blender (Z-up, Y-forward)
        bl_verts = np.column_stack([verts[:, 0], verts[:, 2], verts[:, 1]])
        
        # Align feet flat to floor plane Z=0.0m
        min_z = np.min(bl_verts[:, 2])
        bl_verts[:, 2] -= min_z
        
        all_smpl_vertices.append(bl_verts)
        
    all_verts_np = np.array(all_smpl_vertices)
    print(f"[✓] Computed inverted-elbow SMPL/SMPL-X 3D human body surface mesh for {len(all_verts_np)} frames: {all_verts_np.shape}")
    return all_verts_np, body_model.faces

def export_objs_and_datasets(verts_np, faces):
    """Exports 6,890-vertex upright SMPL OBJ sequence files and numpy animation datasets."""
    print("[*] Step 4: Exporting 6,890-vertex OBJ sequence and numpy animation datasets...")
    os.makedirs(OBJ_DIR, exist_ok=True)
    
    # Clear old OBJs
    for p in glob.glob(os.path.join(OBJ_DIR, "*.obj")):
        os.remove(p)
        
    min_hip_idx = 0
    min_hip_z = 999.0
    
    for i in range(len(verts_np)):
        obj_file = os.path.join(OBJ_DIR, f"frame_{i:04d}.obj")
        with open(obj_file, "w") as f:
            f.write("# Upright EasyMocap SMPL/SMPL-X 3D Human Body Surface Mesh\n")
            for v in verts_np[i]:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                
        avg_z = np.mean(verts_np[i][:, 2])
        if avg_z < min_hip_z:
            min_hip_z = avg_z
            min_hip_idx = i

    # Copy single peak depth OBJ
    shutil.copyfile(os.path.join(OBJ_DIR, f"frame_{min_hip_idx:04d}.obj"), SINGLE_OBJ_PATH)
    
    # Save numpy datasets
    np.save(os.path.join(VIDEOS2_DIR, "squat_vertices_anim.npy"), verts_np)
    np.save(os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy"), verts_np[:, :33, :])
    np.save(os.path.join(VIDEOS2_DIR, "squat_anchored_anim.npy"), verts_np)
    np.save(os.path.join(VIDEOS2_DIR, "squat_male_anim.npy"), verts_np)
    
    print(f"[✓] Exported {len(verts_np)} 6,890-vertex OBJ sequence files to {OBJ_DIR}")

def build_blender_and_glb():
    """Assembles Blender projects and exports web-playable GLB 3D animations with clean 0° transform."""
    print("[*] Step 5: Assembling Blender project files & exporting rigged GLB animations...")
    blender_script = os.path.join(VIDEOS2_DIR, "build_easymocap_blend.py")
    
    script_content = f"""import bpy
import os
import glob

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for m in bpy.data.meshes:
    bpy.data.meshes.remove(m)

single_obj = r'{SINGLE_OBJ_PATH}'
blend_out = r'{BLEND_OUT_PATH}'
single_blend = r'{SINGLE_BLEND_PATH}'
glb_out = r'{GLB_OUT_PATH}'
single_glb = r'{SINGLE_GLB_PATH}'
obj_dir = r'{OBJ_DIR}'

# Single blend
bpy.ops.wm.obj_import(filepath=single_obj, forward_axis='Y', up_axis='Z')
if len(bpy.context.selected_objects) > 0:
    actor = bpy.context.selected_objects[0]
    actor.name = 'EasyMocap_SMPL_Actor'
    actor.rotation_euler = (0, 0, 0)

bpy.ops.wm.save_as_mainfile(filepath=single_blend)
bpy.ops.export_scene.gltf(filepath=single_glb, export_format='GLB')

# Animated shape key blend
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

obj_files = sorted(glob.glob(os.path.join(obj_dir, '*.obj')))
bpy.ops.wm.obj_import(filepath=obj_files[0], forward_axis='Y', up_axis='Z')
actor = bpy.context.selected_objects[0]
actor.name = 'EasyMocap_SMPL_Actor'
actor.rotation_euler = (0, 0, 0)

actor.shape_key_add(name='Basis', from_mix=False)
sk_data = actor.data.shape_keys
sk_data.use_relative = True

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(obj_files)

for i, obj_p in enumerate(obj_files):
    frame_num = i + 1
    verts = []
    with open(obj_p, 'r') as ofile:
        for line in ofile:
            if line.startswith('v '):
                parts = line.strip().split()
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
    key_name = 'Frame_%04d' % frame_num
    key = actor.shape_key_add(name=key_name, from_mix=False)
    if len(verts) == len(actor.data.vertices):
        for v_idx, pos in enumerate(verts):
            key.data[v_idx].co = pos
    key.value = 0.0
    key.keyframe_insert(data_path='value', frame=frame_num - 1)
    key.value = 1.0
    key.keyframe_insert(data_path='value', frame=frame_num)
    key.value = 0.0
    key.keyframe_insert(data_path='value', frame=frame_num + 1)

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB', export_morph=True)
"""
    with open(blender_script, "w") as f:
        f.write(script_content)
        
    cmd = ["blender", "-b", "--python", blender_script]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"[✓] Successfully built Blender projects & GLB outputs:")
    print(f"    - {BLEND_OUT_PATH}")
    print(f"    - {GLB_OUT_PATH}")

def main():
    print("==========================================================================")
    print("  EasyMocap SMPL/SMPL-X Motion Capture & Inverted Elbow Flexion Pipeline   ")
    print("==========================================================================")
    
    calibrate_cameras()
    extract_2d_keypoints()
    verts_np, faces = synthesize_scripted_squat_smpl()
    export_objs_and_datasets(verts_np, faces)
    build_blender_and_glb()
    
    print("\n[DONE] Synthetic authored squat animation written. NOT a capture result —\n       do not present these meshes as motion capture output.")

if __name__ == "__main__":
    main()
