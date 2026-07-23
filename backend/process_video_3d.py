import os
import sys
import glob
import time
import json
import cv2
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Add 4D-Humans directory to python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUMANS_DIR = os.path.join(SCRIPT_DIR, "4D-Humans")
sys.path.append(HUMANS_DIR)

# Monkeypatch torch.load to bypass PyTorch 2.6 weights_only=True
_orig_load = torch.load
def _new_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _orig_load(*args, **kwargs)
torch.load = _new_load

from hmr2.configs import CACHE_DIR_4DHUMANS
from hmr2.models import HMR2, download_models, load_hmr2, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset, DEFAULT_MEAN, DEFAULT_STD
from hmr2.utils.renderer import Renderer, cam_crop_to_full
import trimesh

LIGHT_BLUE = (0.65098039, 0.74117647, 0.85882353)

def process_video(video_path, output_dir, target_fps=15, detector_type='regnety'):
    os.makedirs(output_dir, exist_ok=True)
    frames_dir = os.path.join(output_dir, "extracted_frames")
    obj_dir = os.path.join(output_dir, "obj_sequence")
    renders_dir = os.path.join(output_dir, "rendered_frames")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(obj_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)

    print(f"[*] Loading video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    total_src_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    frame_interval = max(1, int(round(src_fps / target_fps)))
    actual_fps = src_fps / frame_interval
    print(f"[✓] Source: {width}x{height} @ {src_fps:.2f}fps ({total_src_frames} frames). Extracting every {frame_interval} frames (~{actual_fps:.2f} fps)...")

    saved_frame_paths = []
    frame_idx = 0
    saved_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            frame_filename = f"frame_{saved_count:04d}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            saved_frame_paths.append(frame_path)
            saved_count += 1
        frame_idx += 1
    cap.release()
    print(f"[✓] Extracted {saved_count} frames to {frames_dir}")

    # Load 4D-Humans models
    print("[*] Initializing HMR2 model & Detector on GPU...")
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2(DEFAULT_CHECKPOINT)
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()

    from hmr2.utils.utils_detectron2 import DefaultPredictor_Lazy
    if detector_type == 'vitdet':
        from detectron2.config import LazyConfig
        import hmr2
        cfg_path = Path(hmr2.__file__).parent/'configs'/'cascade_mask_rcnn_vitdet_h_75ep.py'
        detectron2_cfg = LazyConfig.load(str(cfg_path))
        detectron2_cfg.train.init_checkpoint = "https://dl.fbaipublicfiles.com/detectron2/ViTDet/COCO/cascade_mask_rcnn_vitdet_h/f328730692/model_final_f05665.pkl"
        for i in range(3):
            detectron2_cfg.model.roi_heads.box_predictors[i].test_score_thresh = 0.25
        detector = DefaultPredictor_Lazy(detectron2_cfg)
    else:
        from detectron2 import model_zoo
        detectron2_cfg = model_zoo.get_config('new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py', trained=True)
        detectron2_cfg.model.roi_heads.box_predictor.test_score_thresh = 0.5
        detectron2_cfg.model.roi_heads.box_predictor.test_nms_thresh = 0.4
        detector = DefaultPredictor_Lazy(detectron2_cfg)

    renderer = Renderer(model_cfg, faces=model.smpl.faces)

    print(f"[*] Processing 3D mesh reconstruction for {len(saved_frame_paths)} frames...")
    start_time = time.time()
    
    video_out_path = os.path.join(output_dir, "3d_mesh_overlay_video.mp4")
    # VideoWriter for combined output: Original + 3D Mesh Rendered side-by-side
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter(video_out_path, fourcc, actual_fps, (width * 2, height))

    kinematics_data = []

    for idx, img_path in enumerate(tqdm(saved_frame_paths, desc="Reconstructing 3D Meshes")):
        img_cv2 = cv2.imread(img_path)
        det_out = detector(img_cv2)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()

        if len(boxes) == 0:
            # Fallback if person missing in a frame: copy frame
            combined_frame = np.concatenate([img_cv2, img_cv2], axis=1)
            out_video.write(combined_frame)
            continue

        # Pick the largest bounding box (main subject)
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

            # 1. Save frame .OBJ mesh file
            obj_filename = f"frame_{idx:04d}.obj"
            obj_filepath = os.path.join(obj_dir, obj_filename)
            tmesh = renderer.vertices_to_trimesh(verts, cam_t, LIGHT_BLUE)
            tmesh.export(obj_filepath)

            # 2. Render 3D Mesh overlay
            misc_args = dict(
                mesh_base_color=LIGHT_BLUE,
                scene_bg_color=(1, 1, 1),
                focal_length=scaled_focal_length,
            )
            cam_view = renderer.render_rgba_multiple([verts], cam_t=[cam_t], render_res=img_size[0], **misc_args)

            input_img = img_cv2.astype(np.float32) / 255.0
            mesh_rgb = cam_view[:, :, :3]
            mesh_alpha = cam_view[:, :, 3:]

            overlay_img = input_img * (1 - mesh_alpha) + mesh_rgb * mesh_alpha
            overlay_img_uint8 = (overlay_img * 255).astype(np.uint8)

            # Save frame png preview
            render_png_path = os.path.join(renders_dir, f"frame_{idx:04d}.png")
            cv2.imwrite(render_png_path, overlay_img_uint8)

            # Side-by-side view: Original | 3D Mesh Rendered
            combined_frame = np.concatenate([img_cv2, overlay_img_uint8], axis=1)
            out_video.write(combined_frame)

            # Store key 3D joint data
            kinematics_data.append({
                "frame": idx,
                "camera_translation": cam_t.tolist(),
                "vertex_count": len(verts),
                "obj_file": obj_filename
            })

    out_video.release()
    elapsed = time.time() - start_time
    print(f"[✓] Finished 3D reconstruction in {elapsed:.2f}s (~{elapsed/len(saved_frame_paths):.3f}s per frame)")
    
    # Save kinematics JSON
    kinematics_path = os.path.join(output_dir, "3d_kinematics.json")
    with open(kinematics_path, "w") as f:
        json.dump(kinematics_data, f, indent=2)

    # Convert first frame mesh to GLB for web 3D viewer
    first_obj = os.path.join(obj_dir, "frame_0000.obj")
    if os.path.exists(first_obj):
        glb_path = os.path.join(output_dir, "3d_mesh_model.glb")
        mesh = trimesh.load(first_obj)
        mesh.export(glb_path)
        print(f"[✓] Exported primary 3D GLB model to {glb_path}")

    # Build Blender Animation Script
    blender_script_path = os.path.join(output_dir, "build_blender_animation.py")
    blend_output_path = os.path.join(output_dir, "3d_mesh_sequence.blend")
    
    blender_script_content = f"""import bpy, os, glob

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

obj_dir = r"{obj_dir}"
obj_files = sorted(glob.glob(os.path.join(obj_dir, "*.obj")))
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

save_path = r"{blend_output_path}"
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"Saved Blender animation to {{save_path}}")
"""
    with open(blender_script_path, "w") as f:
        f.write(blender_script_content)

    print(f"[✓] Created Blender script: {blender_script_path}")
    print("[*] Generating Blender 3D animation project file...")
    os.system(f"blender --background --python \"{blender_script_path}\"")
    
    print("\n==========================================")
    print(f"[✓] SUCCESS: 3D Mesh conversion complete!")
    print(f"Output directory: {output_dir}")
    print(f"  1. 3D OBJ Sequence: {obj_dir}")
    print(f"  2. 3D GLB Model: {os.path.join(output_dir, '3d_mesh_model.glb')}")
    print(f"  3. Blender Project: {blend_output_path}")
    print(f"  4. 3D Mesh Overlay Video: {video_out_path}")
    print("==========================================")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_input = sys.argv[1]
    else:
        video_input = "/home/pd/Downloads/20260723_121036.mp4"

    if len(sys.argv) > 2:
        out_dir = sys.argv[2]
    else:
        video_stem = Path(video_input).stem
        out_dir = os.path.join(os.path.dirname(video_input), f"{video_stem}_3d_mesh")

    target_fps = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    process_video(video_input, out_dir, target_fps=target_fps)
