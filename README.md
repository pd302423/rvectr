# Rvectr

Rvectr is a school research project about measuring human movement in 3D with
ordinary phone cameras. It tests one movement, the squat, and one number, the
depth of the squat (how far the hips drop). It is an entry for the CBSE Science
Exhibition 2026-27, sub-theme "AI for Better Life".

> [!IMPORTANT]
> **Validation available so far uses generated data.**
> Everything checked so far uses synthetic data. That means data made by a
> computer program, where the right answer is known in advance. These checks show
> that the software can recover a known answer. They do not show that phone
> cameras are accurate. The first real-phone pilot will compare the reconstructed
> depths with blinded readings of a pelvis marker against a measured scale.

[Current exhibition write-up](docs/writeups/CBSE_2026_27.md) · [First recording](docs/PILOT_RECORDING_CHECKLIST.md)

## The research question

How do camera count and movement speed affect the accuracy of vertical
squat-depth estimates from ordinary phones?

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
   hips. The software tracks its height over time. A nearby pair of valid observations can be resampled at a common time.
   A missing hip or long gap stays missing.
6. **Measure the depth of each squat.** The standing height is the median pelvis
   height while the person stands still (the median is the middle value, so odd
   wild values are ignored). The bottom is the lowest point of a parabola (a
   smooth U-shaped curve) fitted to the frames near the bottom. Depth is the
   standing height minus the bottom.
7. **Compare with a reference squat.** The pilot identifies one baseline attempt in the independent annotation sheet. Each squat is then labelled "reached reference", "shallower" or
   "unclear". "Unclear" means too little of the squat was seen to decide.

Measuring with one camera, or with pairs of cameras, exists only to compare
against the full set of cameras on the same take. It is not a way to run a
session. The full method, with every setting explained, is in
[docs/TWO_CAMERA_PIPELINE.md](docs/TWO_CAMERA_PIPELINE.md).

### Error budget (a simulation)

Before any real recording, a Monte Carlo simulation compares camera setups on
computer-made squats. It adds stated keypoint noise, missing frames,
motion-dependent noise, phone timing offsets, shared camera biases and
per-camera calibration errors. These are sensitivity settings, not measured
phone error rates. The baseline is 60 fps; the frame-rate sensitivity uses
30 fps. The camera layout is side-on plus a 45° oblique view, with a mirrored
oblique third view when enabled.

For the best-threshold comparison, matching sessions are split in half: the
first half sets one cutoff and selects the first tested depth-grid point meeting
the 95% shallow-detection and 5% matching-false-alarm limits. Unclear attempts
remain in both denominators and count as not detected. Three test attempts in a
session share the same reference, so uncertainty intervals resample complete
sessions. The other half checks that frozen cutoff once. The summary reports
the tested grid bracket, training and held-out counts, rates and pass/fail; it
does not interpolate between grid points or search the held-out sessions for a
new passing value. The software's fixed 3 cm tolerance is a separate rule.

The separate 3 mm check sets a cutoff on 300 training sessions and evaluates
it on 300 held-out sessions, giving 900 attempts in each held-out class.
The compact summary in `src/lib/results/simulation-summary.json` records the
named run, seed, units, settings, dependency versions and source hashes.
The site and poster both read this file.

To reproduce the full run from the repository root, use a fresh output directory.
The wildcard in the export command then selects exactly the run just created.

```bash
mkdir -p outputs/sim
run_root=$(mktemp -d outputs/sim/reproduce-XXXXXX)
uv run --no-sync python tools/run_error_budget.py --workers 12 --seed 1 --out-root "$run_root"
uv run --no-sync python tools/export_simulation_summary.py --summary "$run_root"/error_budget_*/summary.json
uv run --no-sync python tools/make_poster_charts.py --summary src/lib/results/simulation-summary.json --out outputs/poster_kit
```

The new run gets its own UTC identifier. Compare its numerical tables with
the versioned summary. On a smaller machine, reduce `--workers`. The seed
and the session split determine the simulated observations. To regenerate
the published poster alone, run the last command against the versioned file.

The simulation does not run RTMPose on real video or validate its error model.
It does not model all production checks and failures, including confidence,
reprojection and ray-angle rejection, robust refinement, lens distortion,
hip swaps, clothing or measured camera-error correlations. Its simulated
multi-view benefit depends on accurate camera calibration and timing.

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
bash tools/bootstrap-linux.sh
```

This installs the locked CPU environment, runs the tests and enables the
contributor publication hook. Add `--pose` for CPU inference, or
`--cuda --pose` for NVIDIA inference. Add `--web` to build the website.
For a minimal CPU setup use `uv sync --frozen` and `uv run --no-sync pytest -q`.

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
exhibition stall. Use Node.js 22 LTS, then:

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
| RTMLib | Inference wrapper | Apache 2.0. |
| RTMPose / MMPose | Hip keypoint model | Apache 2.0 for code. See LICENSE for weight attribution. |

## Not a medical device

Rvectr is a research prototype. It is not a medical or diagnostic device. Its
accuracy has not been validated against any reference standard, and no accuracy
claim is made. Do not use it to make medical, rehabilitation or training
decisions where a wrong result could cause harm.
