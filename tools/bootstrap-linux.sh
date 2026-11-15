#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.local/bin:$PATH"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-600}"
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-4}"
with_pose=0
with_web=0
for argument in "$@"; do
  case "$argument" in
    --pose) with_pose=1 ;;
    --web) with_web=1 ;;
    *) printf 'Unknown option: %s\n' "$argument" >&2; exit 2 ;;
  esac
done
if [[ "$(uname -s)" != Linux ]]; then
  printf '%s\n' 'Run this inside WSL 2 or native Linux.' >&2
  exit 1
fi
if ! command -v uv >/dev/null; then
  printf '%s\n' 'Install uv 0.13.6: curl -LsSf https://astral.sh/uv/0.13.6/install.sh | sh' >&2
  exit 1
fi
for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null; then
    printf 'Missing system dependency: %s\n' "$tool" >&2
    exit 1
  fi
done
uv python install 3.11
sync_arguments=(--frozen --extra cuda)
if [[ "$with_pose" == 1 ]]; then sync_arguments+=(--extra pose); fi
uv sync "${sync_arguments[@]}"
uv run --no-sync rvectr doctor --require-cuda
uv run --no-sync pytest -q
if [[ "$with_web" == 1 ]]; then
  command -v npm >/dev/null || { printf '%s\n' 'Install a supported Node.js LTS and npm first.' >&2; exit 1; }
  npm ci --no-audit --no-fund
  NEXT_TELEMETRY_DISABLED=1 npm run build
fi
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git config core.hooksPath .githooks
fi
printf '%s\n' 'Linux environment checks passed. Camera calibration and measurement accuracy remain separate checks.'
