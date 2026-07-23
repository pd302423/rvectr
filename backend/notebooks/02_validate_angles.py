import json
import numpy as np

def main():
    with open('../squat_kinematics.json', 'r') as f:
        data = json.load(f)
        
    angles_to_check = ['left_knee_angle', 'right_knee_angle', 'left_hip_angle', 'right_hip_angle', 'torso_lean']
    segments = ['l_femur_len', 'r_femur_len', 'l_tibia_len', 'r_tibia_len', 'torso_len']
    
    pass_validation = True
    suspicious_frames = set()
    
    report = []
    report.append("=== Biomechanical Plausibility Validation ===")
    
    # Check angles 0 to 180
    for i, frame in enumerate(data):
        for angle_name in angles_to_check:
            val = frame.get(angle_name)
            if val is not None and (val < 0 or val > 180):
                report.append(f"Frame {frame['frame']} {angle_name} out of bounds: {val:.2f}°")
                suspicious_frames.add(frame['frame'])
                pass_validation = False
                
    # Check segment length constancy (>5% or >2%)
    for seg in segments:
        vals = [f[seg] for f in data if f.get(seg) is not None]
        if vals:
            mean_len = np.mean(vals)
            max_var = np.max(np.abs(vals - mean_len)) / mean_len
            if max_var > 0.05:
                report.append(f"Segment {seg} varies > 5%: max variation {max_var*100:.2f}%")
                pass_validation = False
            elif max_var > 0.02:
                report.append(f"Segment {seg} varies > 2%: max variation {max_var*100:.2f}%")
                
    # Temporal consistency (angle changes < 30°/frame)
    for i in range(1, len(data)):
        prev = data[i-1]
        curr = data[i]
        for angle_name in angles_to_check:
            val_p = prev.get(angle_name)
            val_c = curr.get(angle_name)
            if val_p is not None and val_c is not None:
                diff = abs(val_c - val_p)
                if diff > 30:
                    report.append(f"Frame {curr['frame']} {angle_name} change exceeds 30°: {diff:.2f}°")
                    suspicious_frames.add(curr['frame'])
                    pass_validation = False
                    
    report.append("\n=== Validation Report ===")
    report.append(f"Overall Status: {'PASS' if pass_validation else 'FAIL'}")
    if suspicious_frames:
        report.append(f"Suspicious Frames: {sorted(list(suspicious_frames))}")
        
    for line in report:
        print(line)

if __name__ == "__main__":
    main()
