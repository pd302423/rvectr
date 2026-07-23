import os
import sys
import pytest
import numpy as np
import trimesh

# Add backend dir to path to import extract_kinematics
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from extract_kinematics import load_j_regressor

SMPL_MODEL_PATH = os.path.join(backend_dir, "EasyMocap", "data", "smplx", "SMPL_NEUTRAL.pkl")
MESH_DIR = os.path.join(backend_dir, "squat_demo_out")

@pytest.fixture(scope="session")
def j_regressor():
    return load_j_regressor(SMPL_MODEL_PATH)

@pytest.fixture(scope="session")
def sample_mesh_vertices():
    import glob
    obj_files = sorted(glob.glob(os.path.join(MESH_DIR, "*.obj")))
    if not obj_files:
        pytest.skip(f"No .obj files found in {MESH_DIR}")
    
    mesh = trimesh.load(obj_files[0], process=False)
    return mesh.vertices

@pytest.fixture
def sample_joints():
    # 24 joints, 3 coordinates
    return np.random.rand(24, 3)
