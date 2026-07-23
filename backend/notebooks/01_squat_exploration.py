import json
import numpy as np

def main():
    with open('../squat_kinematics.json', 'r') as f:
        data = json.load(f)
    
    joint_angles = ['left_knee_angle', 'right_knee_angle', 'left_hip_angle', 'right_hip_angle']
    angular_vels = ['left_knee_angular_vel', 'right_knee_angular_vel', 'left_hip_angular_vel', 'right_hip_angular_vel']
    
    report = []
    
    # Summary statistics for joint angles
    report.append("=== Joint Angles Summary ===")
    for metric in joint_angles:
        vals = [frame[metric] for frame in data if frame[metric] is not None]
        if vals:
            report.append(f"{metric}: Min={np.min(vals):.2f}, Max={np.max(vals):.2f}, Mean={np.mean(vals):.2f}, Std={np.std(vals):.2f}")
    
    # Identify deepest squat frame
    depths = [frame.get('squat_depth', 0) for frame in data]
    min_idx = np.argmin(depths)
    report.append(f"\nDeepest squat frame: {data[min_idx].get('frame', min_idx)} (Depth: {depths[min_idx]:.2f})")
    
    # Knee valgus frames
    valgus_frames = [frame.get('frame', i) for i, frame in enumerate(data) if frame.get('knee_distance', 1.0) < 0.2]
    report.append(f"\nFrames with potential knee valgus: {valgus_frames}")
    
    # Angular velocity statistics
    report.append("\n=== Angular Velocity Summary ===")
    for metric in angular_vels:
        vals = [frame[metric] for frame in data if frame[metric] is not None]
        if vals:
            report.append(f"{metric}: Min={np.min(vals):.2f}, Max={np.max(vals):.2f}, Mean={np.mean(vals):.2f}, Std={np.std(vals):.2f}")
            
    # Symmetry
    knee_diffs = [abs(f['left_knee_angle'] - f['right_knee_angle']) for f in data if f['left_knee_angle'] is not None and f['right_knee_angle'] is not None]
    hip_diffs = [abs(f['left_hip_angle'] - f['right_hip_angle']) for f in data if f['left_hip_angle'] is not None and f['right_hip_angle'] is not None]
    report.append(f"\n=== Left-Right Symmetry (Absolute Differences) ===")
    report.append(f"Knee Mean Diff: {np.mean(knee_diffs):.2f} (Std: {np.std(knee_diffs):.2f})")
    report.append(f"Hip Mean Diff: {np.mean(hip_diffs):.2f} (Std: {np.std(hip_diffs):.2f})")
    
    # Movement phases
    phases = []
    for i, frame in enumerate(data):
        vel = frame.get('velocity', 0)
        if vel is None: vel = 0
        if abs(vel) < 0.1:
            phases.append("STANDING")
        elif vel > 0.1:
            phases.append("DESCENDING")
        else:
            phases.append("ASCENDING")
            
    report.append(f"\nPhases Example (first 10): {phases[:10]}")
    
    out_text = "\n".join(report)
    print(out_text)
    with open('squat_analysis_report.txt', 'w') as f:
        f.write(out_text)
        
if __name__ == "__main__":
    main()
