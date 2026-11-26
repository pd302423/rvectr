# Linux and WSL setup

From the root of a clone, use Linux Python 3.11, uv 0.13.6–0.13.x, FFmpeg and ffprobe.
Install FFmpeg with the distribution's package manager. The bootstrap installs the
locked Python environment, checks the tools, runs pytest and enables the local
pre-push check. Node 22 LTS was used for the website.

```bash
bash tools/bootstrap-linux.sh                  # CPU tools and tests
bash tools/bootstrap-linux.sh --pose           # CPU detector for a recording
bash tools/bootstrap-linux.sh --cuda --pose    # optional NVIDIA detector and CUDA check
```

Add `--web` to also install the locked Node packages and build the site. The
website build downloads the configured fonts. Use `uv run --no-sync` after
setup. The CPU pose extra is `pose-cpu`. The GPU pose extra is `pose` with
`cuda`. Match the session's `pose.device` to the chosen runtime. The first
RTMLib inference downloads detector and pose weights. On WSL use the Windows
NVIDIA driver for the GPU option. The older EasyMocap and SMPL tools have
separate requirements.

## Private local paths

Copy `.env.example` to `.env.local` and set your own recording, calibration,
model and output roots. Use capture names relative to those roots. Preserve
the original video timestamps. Place the checkerboard and stick observations
with the recordings. Keep labels and outputs in your private data directory.

```bash
uv run --no-sync rvectr doctor
uv run --no-sync rvectr run --help
uv run --no-sync pytest -q
```

Use the [pilot recording checklist](PILOT_RECORDING_CHECKLIST.md) and
[two-camera commands](TWO_CAMERA_PIPELINE.md) for a measurement run.
`configs/capture_v1.json` belongs to the separate legacy diagnostic entry
point. The optional PowerShell wrapper (`tools/run-wsl.ps1`) runs `rvectr`
inside WSL from one fixed folder in your WSL home folder. If your checkout is
somewhere else, edit the path in that script or use the Linux shell directly.

## Publication checks

From the branch you plan to submit, run the contributor check. For an owner
audit, fetch the full upstream branches and tags and run the history check.

```bash
uv run --no-sync python tools/check_publish.py
uv run --no-sync python tools/check_publish.py --history
```

The first checks untracked, staged and working changes and commits since the
common main base. The hook checks the commits introduced by each ref being
pushed. Use `--base <commit>` to select an explicit local comparison base.
If a checkout has no main ref, the local check covers the current branch's
reachable commits. Fetch main to narrow that comparison to your own branch.
The full audit also checks the tracked tree and reachable historical blobs,
including files removed in later commits. The owner keeps a private audit of
older files in the Git history.
