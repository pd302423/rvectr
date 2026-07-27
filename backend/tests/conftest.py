"""
Shared fixtures.

Two fixtures below depend on artefacts that are deliberately not in the
repository — the SMPL body model (separately licensed by MPI, never
redistributed) and a recovered OBJ mesh sequence (generated output, gitignored).
Tests that need them skip with an actionable reason rather than failing.

That is why `get_joints` is *also* covered by a synthetic-input test in
test_kinematics.py: a function whose only coverage skips on CI is not covered.
"""

import os
import sys

import numpy as np
import pytest
import trimesh

# Add backend dir to path to import extract_kinematics
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import rvectr_paths
from extract_kinematics import load_j_regressor


@pytest.fixture(scope="session")
def j_regressor():
    """The real (24, 6890) SMPL joint regressor. Skips when the model is absent."""
    if not rvectr_paths.have_smpl_model():
        pytest.skip(rvectr_paths.SMPL_MODEL_HELP)
    return load_j_regressor(rvectr_paths.SMPL_MODEL)


@pytest.fixture(scope="session")
def sample_mesh_vertices():
    """
    Vertices of the first recovered mesh in RVECTR_OUT_DIR.

    Honours RVECTR_OUT_DIR rather than hardcoding squat_demo_out, so pointing the
    variable at a real recovery run actually enables this test.
    """
    import glob

    obj_files = sorted(glob.glob(os.path.join(rvectr_paths.OUT_DIR, "*.obj")))
    if not obj_files:
        pytest.skip(
            f"No .obj mesh sequence in {rvectr_paths.OUT_DIR} (generated output, "
            "not committed). Run a recovery pass or set RVECTR_OUT_DIR to one."
        )

    mesh = trimesh.load(obj_files[0], process=False)
    return mesh.vertices


@pytest.fixture
def sample_joints():
    """24 joints, 3 coordinates. Seeded so a failure reproduces."""
    rng = np.random.default_rng(0)
    return rng.random((24, 3))
