import argparse
import os
import glob
import json
import csv
import numpy as np
from pathlib import Path
import sys

# Try to import extraction tools, assuming they exist in the backend
try:
    from extract_kinematics import load_regressor, extract_joints_from_meshes
except ImportError:
    # Mocks for demonstration if extract_kinematics is not in python path yet
    def load_regressor(path): return None
    def extract_joints_from_meshes(obj_files, regressor): 
        # Return dummy data shape (N, 24, 3)
        return np.zeros((len(obj_files), 24, 3))

from .gait_events import detect_foot_strikes, detect_toe_offs, detect_gait_cycles
from .stride_metrics import cadence, stride_symmetry, flight_time, ground_contact_time
from .pelvic_analysis import arm_swing_symmetry, trendelenburg_score

# SMPL Joint Indices (as specified)
PELVIS = 0
L_HIP = 1
R_HIP = 2
L_KNEE = 4
R_KNEE = 5
L_ANKLE = 7
R_ANKLE = 8
L_FOOT = 10
R_FOOT = 11
L_SHOULDER = 16
R_SHOULDER = 17
L_WRIST = 20
R_WRIST = 21

def process_video_directory(video_dir: str, regressor, fps: float):
    """Processes a single video directory containing .obj files."""
    obj_files = sorted(glob.glob(os.path.join(video_dir, "*.obj")))
    if not obj_files:
        return None
        
    # Extract 3D joint positions (N, NumJoints, 3)
    joints_3d = extract_joints_from_meshes(obj_files, regressor)
    
    # Extract specific joints
    l_ankle = joints_3d[:, L_ANKLE, :]
    r_ankle = joints_3d[:, R_ANKLE, :]
    
    # Ankle Y positions for gait events
    ankle_y = np.stack([l_ankle[:, 1], r_ankle[:, 1]], axis=1)
    
    # Simple dynamic threshold based on bottom 10% of Y positions
    threshold = np.percentile(ankle_y, 10)
    
    # Detect events
    strikes = detect_foot_strikes(ankle_y, threshold, fps)
    toe_offs = detect_toe_offs(ankle_y, threshold, fps)
    gait_cycles = detect_gait_cycles(strikes, toe_offs)
    
    if not gait_cycles:
        return None
        
    left_cycles = [c for c in gait_cycles if c['side'] == 'left']
    right_cycles = [c for c in gait_cycles if c['side'] == 'right']
    
    # Calculate metrics
    metrics = {
        'cadence_spm': cadence(gait_cycles, fps),
        'stride_symmetry_index': stride_symmetry(left_cycles, right_cycles, fps),
        'arm_swing_symmetry_index': arm_swing_symmetry(joints_3d[:, L_WRIST, :], joints_3d[:, R_WRIST, :], fps),
        'avg_flight_time_ms': np.mean(flight_time(gait_cycles, fps)) if flight_time(gait_cycles, fps) else 0.0,
        'num_cycles': len(gait_cycles)
    }
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description="Batch process running/gait analysis from SMPL meshes.")
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing video subdirectories.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save JSON/CSV results.")
    parser.add_argument("--regressor_path", type=str, default="data/J_regressor_extra.npy", help="Path to SMPL joint regressor.")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second of the source videos.")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading regressor from {args.regressor_path}...")
    regressor = load_regressor(args.regressor_path)
    
    video_dirs = [d for d in input_path.iterdir() if d.is_dir()]
    print(f"Found {len(video_dirs)} video directories to process.")
    
    summary_data = []
    
    for i, vdir in enumerate(video_dirs):
        print(f"[{i+1}/{len(video_dirs)}] Processing {vdir.name}...")
        try:
            metrics = process_video_directory(str(vdir), regressor, args.fps)
            if metrics:
                metrics['video_name'] = vdir.name
                
                # Save individual JSON
                json_path = output_path / f"{vdir.name}_metrics.json"
                with open(json_path, 'w') as f:
                    json.dump(metrics, f, indent=4)
                    
                summary_data.append(metrics)
            else:
                print(f"  No valid gait cycles found in {vdir.name}.")
        except Exception as e:
            print(f"  Error processing {vdir.name}: {e}")
            
    # Save combined CSV
    if summary_data:
        csv_path = output_path / "batch_summary.csv"
        keys = summary_data[0].keys()
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(summary_data)
        print(f"Successfully processed {len(summary_data)} videos. Summary saved to {csv_path}.")
    else:
        print("No videos were successfully processed.")

if __name__ == "__main__":
    main()
