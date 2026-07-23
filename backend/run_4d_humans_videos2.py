#!/usr/bin/env python3
"""
run_4d_humans_videos2.py

Runs 4D-Humans HMR2 SMPL body mesh recovery on `videos2/CE 3/VID_20260723_202801.mp4`:
1. Rotates video 180° so the athlete is upright.
2. Predicts 6,890-vertex 3D SMPL human body surface mesh for every frame.
3. Exports full-body SMPL 3D human OBJ meshes into `videos2/obj_sequence/` and `videos2/squat_3d_mesh.obj`.
4. Assembles realistic 3D human body Blender files (`videos2/squat_3d_mesh.blend` and `videos2/squat_multiview_animated.blend`).
"""

import os
import sys
import glob
import time
import subprocess
import cv2
import torch
import numpy as np
from tqdm import tqdm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUMANS_DIR = os.path.join(SCRIPT_DIR, "4D-Humans")
sys.path.append(HUMANS_DIR)

# Bypass PyTorch 2.6 weights_only
_orig_load = torch.load
def _new_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _orig_load(*args, **kwargs)
torch.load = _new_load

from hmr2.configs import CACHE_DIR_4DHUMANS
from hmr2.models import HMR2, download_models, load_hmr2, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset
from hmr2.utils.renderer import Renderer, cam_crop_to_full
import trimesh

VIDEOS2_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "videos2"))
VIDEO_PATH = os.path.join(VIDEOS2_DIR, "CE 3", "VID_20260723_202801.mp4")
OUTPUT_DIR = VIDEOS2_DIR
OBJ_DIR = os.path.join(VIDEOS2_DIR, "obj_sequence")
SINGLE_OBJ_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.obj")
BLEND_OUT_PATH = os.path.join(VIDEOS2_DIR, "squat_multiview_animated.blend")
SINGLE_BLEND_PATH = os.path.join(VIDEOS2_DIR, "squat_3d_mesh.blend")

def main():
    os.makedirs(OBJ_DIR, exist_ok=True)
    print(f"[*] Processing 3D Human SMPL Mesh for video: {VIDEO_PATH}")

    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)

    # Frame extraction (extract every frame or step 2 for performance)
    step = 2
    extracted_frames = []
    frame_idx = 0

    temp_frames_dir = os.path.join(VIDEOS2_DIR, "temp_frames")
    os.makedirs(temp_frames_dir, exist_ok=True)

    print(f"[*] Extracting frames (step={step})...")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step == 0:
            # Apply 180° rotation correction for upside-down recording
            rotated = cv2.rotate(frame, cv2.ROTATE_180)
            f_path = os.path.join(temp_frames_dir, f"frame_{len(extracted_frames):04d}.jpg")
            cv2.imwrite(f_path, rotated)
            extracted_frames.append(f_path)
        frame_idx += 1
    cap.release()
    print(f"[✓] Extracted {len(extracted_frames)} frames.")

    print("[*] Loading 4D-Humans HMR2 Model on GPU...")
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2(DEFAULT_CHECKPOINT)
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()

    from detectron2 import model_zoo
    from hmr2.utils.utils_detectron2 import DefaultPredictor_Lazy
    detectron2_cfg = model_zoo.get_config('new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py', trained=True)
    detectron2_cfg.model.roi_heads.box_predictor.test_score_thresh = 0.4
    detector = DefaultPredictor_Lazy(detectron2_cfg)
    renderer = Renderer(model_cfg, faces=model.smpl.faces)

    all_verts = []
    min_y_val = 999.0
    min_y_idx = 0

    print(f"[*] Predicting 6,890-vertex 3D SMPL meshes for {len(extracted_frames)} frames...")
    for idx, img_path in enumerate(tqdm(extracted_frames)):
        img_cv2 = cv2.imread(img_path)
        det_out = detector(img_cv2)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.4)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()

        if len(boxes) == 0:
            # If person missed in frame, fallback to previous or dummy
            if len(all_verts) > 0:
                verts = all_verts[-1]
            else:
                verts = np.zeros((6890, 3))
            cam_t = np.array([0, 0, 2.5])
        else:
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            main_box_idx = np.argmax(areas)
            main_box = boxes[main_box_idx:main_box_idx+1]

            dataset = ViTDetDataset(model_cfg, img_cv2, main_box)
            dataloader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)

            for batch in dataloader:
                batch = recursive_to(batch, device)
                with torch.no_grad():
                    out = model(batch)
                pred_cam = out['pred_cam']
                box_center = batch["box_center"].float()
                box_size = batch["box_size"].float()
                img_size = batch["img_size"].float()
                scaled_focal_length = model_cfg.EXTRA.FOCAL_LENGTH / model_cfg.MODEL.IMAGE_SIZE * img_size.max()
                pred_cam_t_full = cam_crop_to_full(pred_cam, box_center, box_size, img_size, scaled_focal_length).detach().cpu().numpy()

                verts = out['pred_vertices'][0].detach().cpu().numpy()
                cam_t = pred_cam_t_full[0]

        all_verts.append(verts)

        # Export SMPL 3D mesh OBJ
        tmesh = renderer.vertices_to_trimesh(verts, cam_t, (0.65, 0.74, 0.85))
        obj_file = os.path.join(OBJ_DIR, f"frame_{idx:04d}.obj")
        tmesh.export(obj_file)

        avg_y = np.mean(verts[:, 1])
        if avg_y < min_y_val:
            min_y_val = avg_y
            min_y_idx = idx

    # Save peak depth single OBJ
    tmesh_single = renderer.vertices_to_trimesh(all_verts[min_y_idx], np.array([0, 0, 2.5]), (0.65, 0.74, 0.85))
    tmesh_single.export(SINGLE_OBJ_PATH)
    print(f"[✓] Saved peak depth SMPL OBJ mesh to {SINGLE_OBJ_PATH} (frame {min_y_idx})")

    # Save vertex numpy animation data
    all_verts_np = np.array(all_verts)
    np.save(os.path.join(VIDEOS2_DIR, "squat_vertices_anim.npy"), all_verts_np)
    np.save(os.path.join(VIDEOS2_DIR, "squat_multiview_anim.npy"), all_verts_np[:, :33, :])

    # Invoke Blender to save .blend scenes
    print("[*] Re-building Blender scenes with 6,890-vertex SMPL body meshes...")
    blender_script_path = os.path.join(VIDEOS2_DIR, "import_objs.py")
    blender_script_content = f"""import bpy
import os
import glob

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Save single blend
bpy.ops.wm.obj_import(filepath=r"{SINGLE_OBJ_PATH}")
bpy.ops.wm.save_as_mainfile(filepath=r"{SINGLE_BLEND_PATH}")

# Save animated blend
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
    with open(blender_script_path, "w") as f:
        f.write(blender_script_content)

    cmd = ["blender", "-b", "--python", blender_script_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"[✓] Successfully generated 3D Human SMPL body meshes for videos2!")

if __name__ == "__main__":
    main()
