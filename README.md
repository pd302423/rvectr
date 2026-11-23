# Rvectr

Rvectr is a school research project about measuring human movement in 3D with
ordinary phone cameras. It tests one movement, the squat, and one number, the
depth of the squat (how far the hips drop). It is an entry for the CBSE Science
Exhibition 2026-27, sub-theme "AI for Better Life".

> [!IMPORTANT]
> **Status: tested on simulated data only.**
> Everything checked so far uses synthetic data. That means data made by a
> computer program, where the right answer is known in advance. These checks show
> that the software can recover a known answer. They do not show that phone
> cameras are accurate. No real recordings have been analysed yet. The next step
> is a pilot recording with real phones. This page makes no accuracy claim.

## The research question

How does the accuracy of 3D movement estimates from ordinary phone cameras
change with the number of camera views and with movement speed?

A "view" is one camera's picture of the person. In plain words: does a second
phone help? Does a third? Is a fast squat measured worse than a slow one?

Squat depth is the test because it is a single number that is easy to compare.
Depth is how far the hips drop between standing and the bottom of the squat.

## How it works

The software is a Python package called `rvectr`. A measurement session needs at
least two phones. It goes through these steps:

1. **Calibrate each phone.** Calibration means measuring the phone, so that
   points in its picture can be turned into real directions in space. We film a
   printed checkerboard. The software finds the lens properties of each phone
   (called intrinsics) and where each phone stands (called extrinsics).
2. **Line up the videos in time.** Phones do not start recording at exactly the
   same moment. A phone torch is flashed in view of all cameras at the start and
   end of each take. The software finds the flash in each video and uses it to
   match the timing.
3. **Find the hips in each video.** A pose-estimation model called RTMPose, run
   through the RTMLib package, marks keypoints (points such as the hips) on
   every frame. Rvectr uses the two hip keypoints.
4. **Triangulate into 3D.** Each camera sees a hip along a straight line. Where
   the lines from two or more cameras cross is the position of the hip in 3D.
   The method used is DLT (direct linear transform).
5. **Follow the pelvis height.** The pelvis is taken as the midpoint of the two
   hips. The software tracks its height over time. Frames where the hips could
   not be found stay missing. Missing data is never filled in.
6. **Measure the depth of each squat.** The standing height is the median pelvis
   height while the person stands still (the median is the middle value, so odd
   wild values are ignored). The bottom is the lowest point of a parabola (a
   smooth U-shaped curve) fitted to the frames near the bottom. Depth is the
   standing height minus the bottom.
7. **Compare with a reference squat.** One squat is the reference (by default the
   first). Each squat is then labelled "reached reference", "shallower" or
   "unclear". "Unclear" means too little of the squat was seen to decide.

Measuring with one camera, or with pairs of cameras, exists only to compare
against the full set of cameras on the same take. It is not a way to run a
session. The full method, with every setting explained, is in
[docs/TWO_CAMERA_PIPELINE.md](docs/TWO_CAMERA_PIPELINE.md).

### Error budget (a simulation)

Before any real recording, a Monte Carlo simulation predicts the smallest change
in squat depth that each camera setup could catch. Monte Carlo means running a
random experiment many times to see how much the results spread. The simulation
adds typical errors (noise in the keypoints, timing errors, calibration errors,
missing frames) to a computer-made squat.

Every number from it is a prediction from a computer model. It is not a
measurement. The model is in `backend/rvectr/errorbudget.py` and the runner is
`tools/run_error_budget.py`. The script `tools/make_poster_charts.py` draws
charts from a finished simulation run, which is stored locally and not in this
repository.

## Repository layout

```
backend/
  rvectr/          the Python package: calibration, sync, pose, 3D, squat depth, error budget
  tests/           automatic tests (they use synthetic data only)
  pipeline/        older gait and running code
  *.py             older scripts (see the caution below)
configs/           example session, calibration and label files
docs/              method notes, checklists and write-ups
src/               the website (Next.js)
public/            static files for the website
tools/             setup script, publish check, simulation runner, chart maker
models/            holds only a README; private model files are kept outside Git
outputs/           holds only a README; run results are written here and not committed
```

The two folders `backend/4D-Humans` and `backend/EasyMocap` are Git submodules
(links to other projects). Only the older scripts use them. A normal clone is
enough for the main pipeline.

> [!CAUTION]
> **Not every older script in `backend/` measures what its name suggests.** For
> example, `run_easymocap_videos2.py` writes a hand-made animation, not a
> measurement. Read [backend/README.md](backend/README.md) and
> [critical_analysis.md](critical_analysis.md) before running or citing any of
> them.

## Quick start

Linux is the main platform. On Windows, use WSL 2 (Linux inside Windows). More
detail is in [docs/LINUX_FIRST.md](docs/LINUX_FIRST.md).

### Python

You need Python 3.11 (installed for you by uv), the package manager
[uv](https://docs.astral.sh/uv/) (version 0.13.6 or a later 0.13 release), and
`ffmpeg` with `ffprobe`.

```bash
git clone https://github.com/pd302423/rvectr.git
cd rvectr
bash tools/bootstrap-linux.sh --pose --web
```

The script installs the locked Python packages, checks the environment, runs the
tests and builds the website (`--pose` adds the pose-detection packages, `--web`
adds the website). It needs an NVIDIA GPU with CUDA and stops if it cannot find
one. Without a GPU, set up the code and run the tests like this instead:

```bash
uv sync --frozen
uv run --no-sync pytest -q
```

Useful commands (always use `uv run --no-sync` so the locked versions are used):

```bash
uv run --no-sync rvectr doctor          # check ffmpeg and the environment
uv run --no-sync pytest -q              # run the tests
uv run --no-sync rvectr run --help      # help for the measurement command
```

The measurement commands are `calibrate-intrinsics`, `calibrate-extrinsics`,
`sync`, `run`, `check-points` and `frames`. Running them on real footage needs
recordings that are not in this repository. You do not need any recordings to
work on the code.

### Website

The website is built with Next.js 16, React 19 and Tailwind CSS 4. It explains the
project, shows the simulated results and has a live webcam demo for the
exhibition stall. Install a current Node.js LTS release, then:

```bash
npm install
npm run dev      # then open http://localhost:3000
npm run lint
npm run build
```

> [!NOTE]
> This version of Next.js differs from older versions. Before changing web code,
> read the guides in `node_modules/next/dist/docs/` (they appear after
> `npm install`). See [AGENTS.md](AGENTS.md).

## Private data stays out of this repository

These are never committed: official SMPL model files, raw recordings, calibration
records, videos or photos of people, generated body meshes, and `.env.local`
(which holds the private locations of data and models). `.env.example` shows the
format. To check a change before publishing, run
`uv run --no-sync python tools/check_publish.py`.

## How to contribute

Contributions are welcome through pull requests, from small fixes to new tests or
documentation. Read [CONTRIBUTING.md](CONTRIBUTING.md) first. It explains the
setup, the branch and commit rules, the checks to run before a pull request, and
how to use an AI coding assistant. If you use one, point it at
[AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) too.

## Licence

> [!WARNING]
> **Research, education and non-profit use only. This project is NOT MIT
> licensed.** Rvectr builds on EasyMocap, whose terms allow only educational,
> research and non-profit use, require that modifications stay open source, and
> forbid commercial use. Those terms apply to the whole repository. Read
> [LICENSE](LICENSE) for the full text and the attributions.

| Component | Used for | Terms |
|---|---|---|
| [EasyMocap](https://github.com/zju3dv/EasyMocap) | older multi-camera scripts (submodule) | Non-commercial, research and education only. The most restrictive, so it governs this project. |
| 4D-Humans / HMR2 | older single-camera scripts (submodule) | MIT. The link and copyright notice are in LICENSE. |
| [SMPL](https://smpl.is.tue.mpg.de) | body model for fitting | Separate model licence. Not included here. Get it yourself and accept its terms. |
| [MediaPipe](https://github.com/google-ai-edge/mediapipe) | live webcam demo on the website | Apache 2.0. |
| RTMPose, through RTMLib | hip detection in the main pipeline | Its own licence applies. It is not yet listed in LICENSE. |

## Not a medical device

Rvectr is a research prototype. It is not a medical or diagnostic device. Its
accuracy has not been validated against any reference standard, and no accuracy
claim is made. Do not use it to make medical, rehabilitation or training
decisions where a wrong result could cause harm.
