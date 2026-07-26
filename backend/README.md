# rvectr backend

Python 3D vision and kinematics pipeline. **Read this before running anything** —
several scripts here are superseded, and one produces synthetic output that must
not be mistaken for a measurement.

## Environments

Three incompatible Python environments. They cannot be merged; 4D-Humans needs
3.10 and EasyMocap needs 3.11.

| Environment | Python | Install | Use for |
|---|---|---|---|
| **core** | 3.11 | `pip install -r requirements-core.txt` | kinematics extraction, mesh smoothing, tests |
| **hmr2** | 3.10 | `pip install -r requirements-hmr2.txt` | 4D-Humans monocular recovery |
| **easymocap** | 3.11 | `./setup_env.sh` | multi-view triangulation |

```bash
python3.11 -m venv .venv-core && source .venv-core/bin/activate
pip install -r requirements-core.txt
pytest tests/          # 31 tests, no GPU or model weights needed
```

## Paths

No script contains a hardcoded absolute path any more. All locations resolve
through `rvectr_paths.py`, overridable by environment variable:

| Variable | Default | Holds |
|---|---|---|
| `RVECTR_OUT_DIR` | `backend/squat_demo_out` | OBJ mesh sequences |
| `RVECTR_RENDER_DIR` | `backend/render_out` | rendered video, `.blend` files |
| `RVECTR_VIDEOS_DIR` | `<repo>/videos2` | multi-view source footage |
| `RVECTR_CACHE_DIR` | `~/.cache/4DHumans` | model weights |

## Which script to run

### Capture and recovery

| Script | Status | Notes |
|---|---|---|
| `run_4d_humans_videos2.py` | **current** | Monocular SMPL recovery. Real. |
| `run_easymocap_videos2.py` | ⚠️ **see warning** | Steps 1–2 real, **step 3 synthesises** |
| `recalibrate_and_reconstruct_3d.py` | current | MediaPipe two-view reconstruction |
| `process_video_3d.py` | current | Single-video end-to-end; takes a path argument |

> [!CAUTION]
> **`run_easymocap_videos2.py` does not perform motion capture.**
> It calibrates cameras and extracts 2D keypoints (both real), then **discards
> the keypoints** and generates a hand-authored sine-wave squat animation from
> hardcoded joint angles. Everything it exports — `obj_sequence/`,
> `squat_multiview_animated.glb`, `squat_3d_mesh.glb`, `squat_vertices_anim.npy`
> — is an animation, **not a measurement**, and must never be presented as
> capture output. See the module docstring and `docs/log/2026-07-26.md`.

### Kinematics

| Script | Status | Notes |
|---|---|---|
| `extract_kinematics.py` | **current** | Joint angles from an OBJ sequence. Entry point. |
| `pipeline/gait_events.py` | current | Foot strike / toe-off detection — tested |
| `pipeline/stride_metrics.py` | current | GCT, cadence, stride length — tested |
| `pipeline/pelvic_analysis.py` | current | Trendelenburg, trunk rotation — **untested** |
| `pipeline/running_kinematics.py` | current | **untested** |

### Mesh post-processing — pick ONE

Seven scripts overlap here, written in sequence as problems were found. Later
ones subsume earlier ones. Prefer the current entry and ignore the rest unless
you need a specific behaviour.

| Script | Status | Notes |
|---|---|---|
| `smooth_and_center_mesh.py` | **current** | Savitzky–Golay smoothing + centering. Has a CLI. |
| `zero_drift_perfect_smpl_builder.py` | current | Adds root-drift anchoring for stationary movements |
| `fix_jitter.py` | superseded | Earliest smoother; no centering, no CLI |
| `fix_smpl_orientation_and_centering.py` | situational | Only when the mesh comes out rotated |
| `lock_stationary_smpl.py` | superseded | Folded into `zero_drift_perfect_smpl_builder.py` |
| `make_perfect_squat_anim.py` | ⚠️ synthetic | Authored animation, not capture |
| `enhance_muscular_anchored_smpl.py` | ⚠️ avoid for measurement | Adjusts body shape for visual appeal. Shape parameters move joint centres, which biases every angle downstream. Presentation only. |

### Utilities

`download_model.py`, `download_hf.py` (model weights) · `convert_obj_to_glb.py`,
`export_obj_and_blend.py`, `import_objs_blender.py` (format conversion) ·
`make_video.py` (overlay video) · `verify_orientation.py` (sanity check)

## Naming caveat

Scripts named `perfect`, `enhance`, or `zero_drift` describe a desired
appearance, not a verified property. Nothing in this directory has been
validated against a reference standard, and no accuracy claim is supported by
anything here. See `docs/RESEARCH_ROADMAP.md` for the work that would change
that.
