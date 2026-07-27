# rvectr 🧬

> **Markerless 3D Human Mesh Recovery & Real-Time Kinematic Telemetry Engine**

`rvectr` reconstructs full 3D human body surface meshes (6,890 SMPL vertices) from consumer-camera video, extracts frame-by-frame joint kinematics, and visualizes real-time joint angular velocity and kinetic curves in an interactive 3D WebGL viewport.

> [!IMPORTANT]
> **Project status (July 2026):** rvectr has pivoted from a SaaS coaching product to an open research program studying **velocity-dependent error in markerless 3D human pose estimation** — benchmarking EasyMocap, 4D-Humans/HMR2, and MediaPipe against synthetic SMPL ground truth. See [`docs/RESEARCH_ROADMAP.md`](docs/RESEARCH_ROADMAP.md) for the research question, methodology, and timeline. The earlier SaaS launch plan is archived in [`docs/archive/`](docs/archive/).

---

## ✨ Core Features

* **Monocular 3D Human Mesh Recovery (HMR2 / 4D-Humans)**: Reconstructs high-density 3D SMPL parametric body meshes directly from single-camera videos.
* **Multi-View 3D Spatial Triangulation (EasyMocap)**: Synchronizes multi-camera recordings to solve single-camera self-occlusions and perform 3D joint triangulation.
* **Real-Time In-Browser Telemetry (MediaPipe + Three.js)**: Runs zero-latency pose estimation and interactive 360° 3D skeleton rendering directly inside web browsers.
* **Kinematics Engine**: Calculates frame-by-frame joint angles (hip depth, knee flexion, spinal alignment), movement phase transitions (eccentric/concentric), and bilateral asymmetries.
* **Dual Viewport & Synchronized Scrubbing**: Synchronizes raw video playback with 3D mesh motion and live waveform telemetric charts.

---

## 🏗️ Architecture Pipeline

```mermaid
graph TD
    A[Video Input: Single-Cam or Multi-Cam] --> B1[EasyMocap Multi-View Triangulation]
    A --> B2[4D-Humans HMR2 Monocular Mesh]
    A --> B3[MediaPipe Pose Browser Client]

    B1 --> C[SMPL 72-Parameter Body Mesh]
    B2 --> C

    C --> D[Kinematic Extraction Engine]
    C --> E[Blender Auto-Rig & Temporal Smoothing]

    D --> F[Kinematics Telemetry JSON]
    E --> G[GLB / OBJ 3D Model Output]

    F --> H[Next.js 16 Web Dashboard & Three.js Canvas]
    G --> H
```

---

## 📁 Repository Structure

```
rvectr/
├── src/                          # Next.js 16 viewer (/, /analysis, /demo, /test/squat, /upload)
│   ├── components/biomechanics/  # ThreeMeshCanvas, KinematicWaveformChart, DualViewport
│   └── lib/cv/                   # Kinematic angle calculations & grading logic
├── backend/                      # Python 3D Vision & Kinematics Pipeline
│   ├── README.md                 # ⚠️ READ FIRST — which script to run, and which not to
│   ├── 4D-Humans/                # Monocular 3D Mesh Recovery Submodule (MIT)
│   ├── EasyMocap/                # Multi-view 3D Triangulation Submodule (Non-Commercial)
│   ├── pipeline/                 # Gait events, stride metrics, pelvic analysis
│   ├── tests/                    # 44 tests — run with `pytest`
│   ├── rvectr_paths.py           # Path resolution (env-overridable, no hardcoded paths)
│   ├── meshio.py                 # Shared OBJ I/O; stamps provenance into every mesh
│   ├── extract_kinematics.py     # Frame-by-frame 3D joint telemetry calculation
│   └── run_4d_humans_videos2.py  # Local GPU inference runner
├── scripts/
│   └── rescue-submodules.sh      # Check/fix unfetchable submodule pointers
├── docs/
│   ├── RESEARCH_ROADMAP.md       # Current research program & 12-week plan
│   ├── ASSETS.md                 # What is not committed, and how to obtain it
│   ├── WORKSPACE_SUMMARY.md      # Architecture & CV stack reference
│   ├── osf_preregistration_draft.md
│   ├── log/                      # Dated engineering log
│   ├── writeups/                 # Science exhibition writeups
│   └── archive/                  # Retired SaaS-era planning docs
├── critical_analysis.md          # Standing audit of known defects & their status
└── LICENSE                       # Research / non-commercial (NOT MIT — see below)
```

> [!CAUTION]
> **Not everything in `backend/` measures what its name suggests.**
> `run_easymocap_videos2.py` calibrates cameras and extracts 2D keypoints, then
> **discards them** and emits a hand-authored animation. Its outputs are not
> capture results — including `squat_3d_mesh.glb` and
> `squat_multiview_animated.glb`, the assets the web viewer renders. Every mesh
> written by the backend now carries a provenance header stating which of these
> it is. Read [`backend/README.md`](backend/README.md) before running or citing
> anything, and [`critical_analysis.md`](critical_analysis.md) for the full list
> of known defects.

---

## 🚀 Quickstart Guide

### 1. Clone the Repository

```bash
git clone https://github.com/pd302423/rvectr.git
cd rvectr
```

> [!WARNING]
> **`--recursive` currently fails.** Both submodules record commits that exist
> only on the original author's machine, while `.gitmodules` still points at the
> upstream repositories. Verify with `./scripts/rescue-submodules.sh --check`;
> that script also performs the fix once you have forked both repos. Until then,
> clone without `--recursive` — the web app and the core test suite do not need
> the submodules.

Once the submodules are pushable:
```bash
git submodule update --init --recursive
```

### 2. Run the Web Application

```bash
# Install frontend dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the viewer.

> [!NOTE]
> **The 3D viewports will be empty on a fresh clone.** Mesh assets (~400 MB of
> `.glb`/`.obj`) are generated output and are not committed. The viewer shows a
> "Mesh asset not found" panel naming the missing file. See
> [`docs/ASSETS.md`](docs/ASSETS.md) for what is missing and why.

`/analysis` displays clearly-labelled **sample data** until a real analysis is
loaded, and `/demo` renders a hand-authored animation behind a banner saying so
— nothing on either page is a measurement.

### 3. Setup Python Backend Pipeline

Three incompatible environments are required (4D-Humans needs Python 3.10,
EasyMocap needs 3.11). Full detail in [`backend/README.md`](backend/README.md).

```bash
cd backend

# Core environment — kinematics, mesh processing, tests. No GPU needed.
python3.11 -m venv .venv-core && source .venv-core/bin/activate
pip install -r requirements-core.txt

pytest    # 44 tests; those needing the licensed SMPL model skip with a reason
```

For the deep-learning backends see `requirements-hmr2.txt` (Python 3.10) and
`setup_env.sh` (EasyMocap).

---

## 📄 License & Attributions

> [!WARNING]
> **Research and non-commercial use only. This project is NOT MIT-licensed.**
>
> rvectr builds on **EasyMocap**, which permits educational, research, and non-profit use only, requires that modifications remain open-source, and prohibits commercial use. Those terms govern this entire repository. See [`LICENSE`](LICENSE) for the full text and the complete attribution list.

| Component | Terms |
|---|---|
| **[EasyMocap](https://github.com/zju3dv/EasyMocap)** | Non-commercial, research/education only — **most restrictive; governs this project** |
| **[4D-Humans / HMR2](https://github.com/shubham-goel/4D-Humans)** | MIT — © 2023 UC Regents, Shubham Goel |
| **[SMPL / SMPL-X](https://smpl.is.tue.mpg.de)** | Separate MPI model license — **not redistributed here**; obtain and accept separately |
| **[MediaPipe](https://github.com/google-ai-edge/mediapipe)** | Apache 2.0 — © Google LLC |

## ⚠️ Not a medical device

This is a research prototype. It is **not** a medical or diagnostic device, and its accuracy has **not been validated against any reference standard**. No accuracy claim is made. Do not use it to inform medical, rehabilitative, or training decisions where inaccuracy could cause harm.
