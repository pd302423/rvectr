"""
Shared path resolution for rvectr backend scripts.

Replaces the hardcoded absolute paths (/home/pd/..., and output written into
another tool's scratch directory) that made every script unrunnable on any
machine but one.

Every location resolves relative to this file, and every one can be overridden
by an environment variable so nothing needs source edits to run elsewhere:

    RVECTR_OUT_DIR      mesh/OBJ working output   (default: backend/squat_demo_out)
    RVECTR_RENDER_DIR   rendered video/blend out  (default: backend/render_out)
    RVECTR_VIDEOS_DIR   multi-view source video   (default: <repo>/videos2)
    RVECTR_CACHE_DIR    model weight cache        (default: ~/.cache/4DHumans)
    RVECTR_SMPL_MODEL   SMPL_NEUTRAL.pkl          (default: inside the EasyMocap submodule)

The SMPL model is NOT redistributed with this repository — it carries a separate
MPI licence that must be accepted individually, and it lives inside a submodule
that CI does not fetch. Anything that needs it must degrade gracefully when it is
absent rather than assuming the developer's local copy. See SMPL_MODEL below.
"""

import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))


def _env_path(var, default):
    return os.path.abspath(os.environ.get(var, default))


# Mesh sequence working directory (OBJ in/out for the smoothing scripts).
OUT_DIR = _env_path("RVECTR_OUT_DIR", os.path.join(BACKEND_DIR, "squat_demo_out"))

# Rendered artifacts: overlay videos, .blend files. Defaults inside the repo
# rather than an external scratch directory.
RENDER_DIR = _env_path("RVECTR_RENDER_DIR", os.path.join(BACKEND_DIR, "render_out"))

# Multi-view source footage.
VIDEOS_DIR = _env_path("RVECTR_VIDEOS_DIR", os.path.join(REPO_ROOT, "videos2"))

# Model weight cache (4D-Humans / HMR2 checkpoints).
CACHE_DIR = _env_path(
    "RVECTR_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".cache", "4DHumans")
)

def _resolve_haar_cascade():
    """
    Locate the frontal-face Haar cascade.

    opencv-python ships this file, so the 930 KB copy that used to be committed
    here was redundant — and it was committed despite a .gitignore rule naming
    it, which made the rule silently inert. Prefer the installed copy; fall back
    to a local file for anyone who still has one.
    """
    name = "haarcascade_frontalface_default.xml"
    try:
        import cv2

        packaged = os.path.join(cv2.data.haarcascades, name)
        if os.path.isfile(packaged):
            return packaged
    except (ImportError, AttributeError):
        pass
    return os.path.join(BACKEND_DIR, name)


HAAR_CASCADE = _resolve_haar_cascade()

# SMPL body model. Separately licensed by MPI and never committed here, so this
# path is frequently absent — on CI, and on any clone that has not fetched the
# submodule and accepted the model licence. Call have_smpl_model() before use.
SMPL_MODEL = _env_path(
    "RVECTR_SMPL_MODEL",
    os.path.join(BACKEND_DIR, "EasyMocap", "data", "smplx", "SMPL_NEUTRAL.pkl"),
)

SMPL_MODEL_HELP = (
    f"SMPL model not found at {SMPL_MODEL}. It is separately licensed by MPI and "
    "is not redistributed with this repository. Obtain it from "
    "https://smpl.is.tue.mpg.de, accept the licence, then either place it at that "
    "path or point RVECTR_SMPL_MODEL at your copy."
)


def have_smpl_model():
    """True if the separately-licensed SMPL body model is available locally."""
    return os.path.isfile(SMPL_MODEL)


def ensure(path):
    """Create a directory if absent and return it."""
    os.makedirs(path, exist_ok=True)
    return path
