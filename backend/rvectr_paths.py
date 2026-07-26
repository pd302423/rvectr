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

# Bundled asset that ships with the repo.
HAAR_CASCADE = os.path.join(BACKEND_DIR, "haarcascade_frontalface_default.xml")


def ensure(path):
    """Create a directory if absent and return it."""
    os.makedirs(path, exist_ok=True)
    return path
