# Linux-first runtime: WSL 2 now, native Linux later

Updated 27 October 2026. WSL Ubuntu 26.04 is the primary current development
environment. Native Windows is secondary. The same Python project, lockfile,
setup script and capture JSON are used on native Linux; local data locations
are configured separately from capture geometry.

## Current working locations

- Original Windows repository, preserved: `C:\Users\Parth Dalal\rvectr`.
- Linux source-only working copy: `/home/parthd/projects/rvectr`.
- Existing recordings are accessed read-only as inputs under
  `/mnt/c/Users/Parth Dalal/Videos/rvectr`.
- Existing model assets remain private under the original project's `models`
  directory. A local `.env.local` points to them; it is not published.
- Code, environments and current outputs live in the Linux filesystem.
- The verified 26 October backup is unchanged by this setup.

The Linux working copy starts a fresh local branch, `codex/linux-first-wsl`,
without copying the original Git history. It has no GitHub remote configured
and has not been pushed. The original working tree and its uncommitted edits
are preserved. Avoid editing both copies independently; continue development
in the Linux copy after this setup.

## Repeatable setup

Install FFmpeg/ffprobe with your Linux distribution's package manager. On WSL,
use the existing Windows NVIDIA driver; do not install a Linux display driver
inside WSL. On native Linux, install the appropriate Linux NVIDIA driver.

Install the pinned uv version and run the shared bootstrap:

```bash
curl -LsSf https://astral.sh/uv/0.13.6/install.sh | sh
cd ~/projects/rvectr
bash tools/bootstrap-linux.sh --pose --web
```

`pyproject.toml` and `uv.lock` pin the scientific dependencies. CUDA uses
PyTorch 2.7.1's CUDA 12.8 wheels as the verified local baseline. The Python `smplx`
package is installed automatically, while official model data is supplied by
the user. ONNX Runtime GPU and RTMLib are pinned in the pose extra and uv.lock.
The package-specific exclusions replace RTMLib's overlapping OpenCV/CPU ONNX
distributions with the project's headless OpenCV and GPU ONNX Runtime.
This is an inference environment, not an MMPose training
environment. Legacy HMR2/EasyMocap scripts need their own optional setup.

The bootstrap runs a real CUDA matrix operation and the test suite. `--web`
also installs the Node dependencies and builds the Next.js application. The
independent Remotion `video` project is excluded from the app's TypeScript build.
Successful environment checks do not validate camera calibration, model fit
accuracy, or the unfinished end-to-end capture pipeline.

## Local configuration

Copy `.env.example` to `.env.local`. For this WSL setup its private values are:

```dotenv
RVECTR_DATA_ROOT="/mnt/c/Users/Parth Dalal/Videos/rvectr"
RVECTR_MODELS_DIR="/mnt/c/Users/Parth Dalal/rvectr/models"
RVECTR_OUTPUT_ROOT="outputs"
```

When moving to native Linux, place your files in the corresponding Linux data
directories or change these local environment variables. Keep
`configs/capture_v1.json` unchanged: its video names are relative to the data
root. Do not transfer a Windows virtual environment.

```bash
uv run --no-sync rvectr doctor --require-cuda
uv run --no-sync rvectr --config configs/capture_v1.json --diagnose-only
uv run --no-sync pytest -q
```

From Windows PowerShell, `tools/run-wsl.ps1 doctor --require-cuda` forwards to
the Linux environment. It uses the WSL user's home directory, not a fixed
Windows account path.

## Calibration is independent of the OS

Each camera entry may specify a calibration JSON filename, resolved relative
to `RVECTR_CALIBRATION_DIR` (default: `<data root>/calibration`). The calibration
record must identify the camera, actual image dimensions and recording mode,
measured intrinsics/distortion, and extrinsics in a common identified physical
coordinate frame. `configs/calibration.example.json` is an **unverified
template**, containing no guessed parameters. The loader rejects mismatched
dimensions, invalid matrices and unconfirmed capture-mode compatibility.

Changing OS or moving a camera does not by itself change lens intrinsics;
moving a camera changes extrinsics. Changing lens, crop, stabilization, focus
or recording mode requires verifying or repeating intrinsic calibration. The
existing 4K moving-board video has unverified compatibility with the v1 camera
settings. The v1 diagnostic therefore remains blocked at calibration.

The diagnostic CLI records metadata, original timestamps, input hashes,
audio alignment candidates, calibration status and software provenance. It
allocates `outputs/V1.1.1`, `V1.1.2`, etc., atomically. Failed and blocked runs
retain their numbers. Pose inference, multiview reconstruction, SMPL fitting
and the viewer still need to be integrated before a real measurement run can
be claimed.

## GitHub publication

Run `python3 tools/check_publish.py --history` before publishing. The original
history includes generated meshes and a video even though they were later
removed from the tracked tree. `.gitignore` does not remove historical
objects. No history was rewritten or force-pushed.

`tools/export_source.py --destination <new-empty-directory>` produces a
filtered source snapshot without `.git`, licensed model data, generated body
assets, recordings, calibration records, environments or credentials. It
checks for obvious embedded credential patterns without printing values.
Retain the source license and attribution notices. Review model, output,
checkpoint and upstream terms separately; excluding model weights alone is
not a general legal clearance.

The next publication decision is whether to use a new source-only repository
or deliberately remediate the existing history. That decision and any push
remain pending. The local `.githooks/pre-push` guard checks reachable history;
it is not a substitute for reviewing the destination repository's existing
branches and tags.

## Setup verification on 27 October

WSL 2 and Ubuntu 26.04 start correctly. Python 3.11.15, uv 0.13.6,
PyTorch 2.7.1+cu128, ONNX Runtime GPU 1.22.0 and RTMLib 0.0.15 are installed.
The RTX 5060 completed a real PyTorch CUDA matrix operation. The final Linux
suite passed **70 tests**, with two optional legacy-data tests skipped. It
includes an ONNX CUDA MatMul with CPU fallback disabled and an optimized-joint
comparison against the official SMPL forward model, using the private licensed
model in memory. These test software/runtime consistency, not capture accuracy.
The web application also passed its production build under Linux Node 22.

Package downloads initially stalled on a CDN route. A temporary WSL hosts-file
selection was used only during installation and the original hosts file was
restored afterward. No NVIDIA display driver was installed inside WSL.

`outputs/V1.1.1` preserves the previous diagnostic. The new Linux diagnostic is
`outputs/V1.1.2`, explicitly `blocked_calibration`; no pose inference or metric
mesh fitting was performed. The source-only working copy passed publication
checks with zero findings. The original Windows Git history still needs
separate review and has not been rewritten or pushed.

References:

- https://docs.nvidia.com/cuda/wsl-user-guide/index.html
- https://docs.astral.sh/uv/getting-started/installation/
- https://pytorch.org/get-started/previous-versions/
- https://smpl.is.tue.mpg.de/modellicense.html
