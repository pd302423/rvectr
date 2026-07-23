"""
03_phase_detection.py — Automatic movement phase detection for squat sequences.

Detects STANDING, DESCENDING, BOTTOM, ASCENDING phases and counts reps.
Thresholds are calibrated to J_regressor-derived kinematics data.
"""
import json
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "squat_kinematics.json")


def detect_phases(data: list[dict]) -> list[str]:
    """
    Assign a movement phase to each frame based on knee angle and pelvis velocity.

    Thresholds are derived from the actual data distribution:
    - Knee angles range ~42° (deep squat) to ~141° (standing)
    - Velocities range ~ -2.0 to +2.0 m/s
    - Positive velocity = pelvis moving down (descending)
    - Negative velocity = pelvis moving up (ascending)
    """
    phases = []

    for frame in data:
        lk = frame.get("left_knee_angle", 180)
        rk = frame.get("right_knee_angle", 180)
        knee = (lk + rk) / 2.0
        vel = frame.get("velocity", 0)

        if knee < 70:
            phase = "BOTTOM"
        elif vel > 0.5:
            phase = "DESCENDING"
        elif vel < -0.5:
            phase = "ASCENDING"
        elif knee > 120 and abs(vel) < 0.3:
            phase = "STANDING"
        else:
            phase = "TRANSITION"

        phases.append(phase)

    return phases


def smooth_phases(phases: list[str], window: int = 5) -> list[str]:
    """
    Apply majority-vote smoothing to remove single-frame noise in phase labels.
    """
    smoothed = phases.copy()
    half = window // 2

    for i in range(half, len(phases) - half):
        local = phases[i - half : i + half + 1]
        # Count occurrences
        counts = {}
        for p in local:
            counts[p] = counts.get(p, 0) + 1
        # Pick most common
        smoothed[i] = max(counts, key=counts.get)

    return smoothed


def count_reps(phases: list[str]) -> list[dict]:
    """
    Count reps by detecting the pattern:
    STANDING → DESCENDING → BOTTOM → ASCENDING → STANDING

    Returns a list of rep dicts with start_frame, end_frame, and bottom_frame.
    """
    reps = []
    state = "IDLE"
    current_rep = None

    for i, phase in enumerate(phases):
        if state == "IDLE" and phase == "STANDING":
            state = "STANDING"
        elif state == "STANDING" and phase == "DESCENDING":
            state = "DESCENDING"
            current_rep = {"start_frame": i}
        elif state == "DESCENDING" and phase == "BOTTOM":
            state = "BOTTOM"
            current_rep["bottom_frame"] = i
        elif state == "BOTTOM" and phase == "ASCENDING":
            state = "ASCENDING"
        elif state == "ASCENDING" and phase in ("STANDING", "TRANSITION"):
            # Allow TRANSITION as end since the athlete might not
            # fully return to STANDING before the next rep
            if phase == "STANDING" or (
                i + 1 < len(phases) and phases[i + 1] in ("STANDING", "DESCENDING")
            ):
                current_rep["end_frame"] = i
                reps.append(current_rep)
                current_rep = None
                state = "STANDING" if phase == "STANDING" else "IDLE"

        # Handle transitions that skip phases (noisy data)
        elif state == "DESCENDING" and phase == "ASCENDING":
            # Went down and came up without hitting BOTTOM threshold
            # Still count it but note it
            current_rep["bottom_frame"] = i - 1
            state = "ASCENDING"
        elif state == "BOTTOM" and phase == "STANDING":
            # Jumped from bottom to standing
            current_rep["end_frame"] = i
            reps.append(current_rep)
            current_rep = None
            state = "STANDING"

    return reps


def main():
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    print(f"=== rvector Phase Detection ===")
    print(f"Loaded {len(data)} frames\n")

    # Detect and smooth phases
    raw_phases = detect_phases(data)
    phases = smooth_phases(raw_phases, window=5)

    # Phase distribution
    from collections import Counter

    counts = Counter(phases)
    print("Phase distribution:")
    for phase, count in sorted(counts.items()):
        pct = count / len(phases) * 100
        print(f"  {phase:15s}: {count:4d} frames ({pct:.1f}%)")
    print()

    # Count reps
    reps = count_reps(phases)
    print(f"Detected {len(reps)} complete reps\n")

    fps = 30.0
    for idx, rep in enumerate(reps):
        start = rep["start_frame"]
        end = rep["end_frame"]
        bottom = rep.get("bottom_frame", start)
        duration = (end - start) / fps

        # Get kinematics for this rep
        rep_data = data[start : end + 1]
        knees = [
            (d["left_knee_angle"] + d["right_knee_angle"]) / 2 for d in rep_data
        ]
        min_knee = min(knees)

        # Angular velocities during descent and ascent
        descent_vels = [
            abs(d.get("left_knee_angular_vel", 0))
            for d in data[start : bottom + 1]
        ]
        ascent_vels = [
            abs(d.get("left_knee_angular_vel", 0))
            for d in data[bottom : end + 1]
        ]

        print(f"--- Rep {idx + 1} ---")
        print(f"  Frames: {start + 1} → {end + 1} (duration: {duration:.2f}s)")
        print(f"  Bottom at frame: {bottom + 1}")
        print(f"  Min knee angle: {min_knee:.1f}°")
        if descent_vels:
            print(f"  Mean descent angular vel: {np.mean(descent_vels):.1f} °/s")
        if ascent_vels:
            print(f"  Mean ascent angular vel: {np.mean(ascent_vels):.1f} °/s")
        print()

    # Save phase labels
    output = {
        "frames": len(data),
        "fps": fps,
        "phases": phases,
        "reps": reps,
        "summary": {
            "total_reps": len(reps),
            "phase_distribution": dict(counts),
        },
    }

    out_path = os.path.join(SCRIPT_DIR, "phase_labels.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Phase labels saved to {out_path}")


if __name__ == "__main__":
    main()
