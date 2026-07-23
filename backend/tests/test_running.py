import unittest
import numpy as np
from pipeline.running_kinematics import detect_gait_phases

class TestRunningKinematics(unittest.TestCase):
    def test_gait_phase_detection(self):
        fps = 30.0
        n_frames = 60 # 2 seconds
        
        # Simulate 2 seconds of running feet Y trajectory
        left_foot_y = np.ones(n_frames) * 0.2
        right_foot_y = np.ones(n_frames) * 0.2
        
        # Left foot touches ground for frames 5 to 12
        left_foot_y[5:13] = 0.0
        # Right foot touches ground for frames 20 to 27
        right_foot_y[20:28] = 0.0
        
        res = detect_gait_phases(left_foot_y, right_foot_y, ground_y=0.0, fps=fps)
        
        self.assertIn("left_gct_ms", res)
        self.assertIn("right_gct_ms", res)
        self.assertIn("cadence_spm", res)
        self.assertGreater(res["cadence_spm"], 0)

if __name__ == "__main__":
    unittest.main()
