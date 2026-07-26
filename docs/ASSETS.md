# Assets: what is not in this repository, and why

A fresh `git clone` gives you the code, not the data. Every 3D viewport in the
web app will show a **"Mesh asset not found"** panel until you supply the assets
below. That is expected, and it is not a bug in the viewer.

Four separate categories, each missing for a different reason. Do not assume one
fix covers another.

---

## 1. Mesh assets for the web viewer — generated output

| Path | Size | Used by |
|---|---|---|
| `public/squat_3d_mesh.glb` | 1.1 MB | `/demo` |
| `public/squat_multiview_animated.glb` | 276 MB | `/analysis`, default `ThreeMeshCanvas` |
| `public/meshes/frame_0000.obj` … `frame_0290.obj` | 121 MB | OBJ frame-scrubbing mode |

**Why they are absent:** `.gitignore` excludes `*.glb` and `*.obj`. Together they
are ~400 MB, which does not belong in git, and `squat_multiview_animated.glb`
alone exceeds what most static hosts will serve.

> [!CAUTION]
> **These specific assets are synthetic.** They descend from
> `backend/synthesize_scripted_squat_anim.py`, which generates a hand-authored
> squat from scripted joint angles. They are **not** capture output and must
> never be presented as a measurement. See `backend/README.md`.

**To regenerate:** run the mesh export chain in `backend/` against a mesh
sequence, then convert with `backend/convert_obj_to_glb.py`. Every OBJ written
through `backend/meshio.py` carries a provenance header — read it before you
trust any mesh you find on disk:

```
# provenance: SYNTHETIC (authored or stylised — NOT a measurement)
```

**If you only want the site to run:** any GLB of a humanoid will render. Point
`glbUrl` at it. Nothing downstream depends on its content.

---

## 2. SMPL / SMPL-X body model — separately licensed

`backend/EasyMocap/data/smplx/SMPL_NEUTRAL.pkl`

**Why it is absent:** the SMPL model carries an MPI licence that must be accepted
individually and does not permit redistribution. It is not ours to ship.

**To obtain it:** register at <https://smpl.is.tue.mpg.de>, accept the licence,
download, then either place it at the path above or point the resolver at your
copy:

```bash
export RVECTR_SMPL_MODEL=/path/to/SMPL_NEUTRAL.pkl
```

Tests needing it skip with an explanatory message rather than failing, so the
suite stays green without it.

---

## 3. Source video — not committed

`videos2/` (multi-view footage), `backend/squat_demo_out/` (recovered meshes).

**Why:** `.gitignore` excludes `*.mp4`, `*.MOV`, `videos/`, `videos2/` and the
`*_demo_out/` directories. These are recordings and derived output, not source.

**Override the locations** rather than moving files:

```bash
export RVECTR_VIDEOS_DIR=/path/to/footage
export RVECTR_OUT_DIR=/path/to/mesh_sequence
```

Pointing `RVECTR_OUT_DIR` at a real mesh sequence also enables the mesh-loading
test that otherwise skips.

---

## 4. Model weights — downloaded on demand

4D-Humans / HMR2 checkpoints, MediaPipe `.task` files.

**Why:** large binaries, and both upstreams distribute them. `.gitignore`
excludes `*.pkl`, `*.pth`, `*.ckpt`, `*.pt`, `*.task`, `*.onnx`.

**To fetch:** `backend/download_model.py`, `backend/download_hf.py`. Cache
location is `RVECTR_CACHE_DIR` (default `~/.cache/4DHumans`).

---

## Summary of environment variables

| Variable | Default | Holds |
|---|---|---|
| `RVECTR_OUT_DIR` | `backend/squat_demo_out` | OBJ mesh sequences |
| `RVECTR_RENDER_DIR` | `backend/render_out` | rendered video, `.blend` files |
| `RVECTR_VIDEOS_DIR` | `<repo>/videos2` | multi-view source footage |
| `RVECTR_CACHE_DIR` | `~/.cache/4DHumans` | model weights |
| `RVECTR_SMPL_MODEL` | inside the EasyMocap submodule | `SMPL_NEUTRAL.pkl` |
