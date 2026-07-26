#!/usr/bin/env bash
#
# Rescue the submodule work that exists only on this machine.
#
# THE PROBLEM
#   backend/EasyMocap and backend/4D-Humans each carry a local commit holding
#   rvectr's changes. .gitmodules points both at their UPSTREAM remotes, which
#   nobody here can push to, so:
#
#     * the work is backed up nowhere, and
#     * the parent repo records a commit that does not exist on the remote it
#       names, which makes `git clone --recursive` fail for everyone.
#
#   Verify at any time with:  ./scripts/rescue-submodules.sh --check
#
# THE FIX
#   Fork both repos to an account you control, push the local commits there, and
#   repoint .gitmodules. This script does everything except create the forks —
#   creating them is yours to do, in the GitHub UI or with `gh repo fork`.
#
# USAGE
#   ./scripts/rescue-submodules.sh --check
#   ./scripts/rescue-submodules.sh --fork-owner <your-github-username>
#   ./scripts/rescue-submodules.sh --easymocap-url <url> --4dhumans-url <url>
#
# The script pushes to remotes. It prints every command and asks before the
# first one that writes anything.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BRANCH="rvectr"
FORK_OWNER=""
EASYMOCAP_URL=""
FOURDH_URL=""
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)           CHECK_ONLY=1; shift ;;
    --fork-owner)      FORK_OWNER="$2"; shift 2 ;;
    --easymocap-url)   EASYMOCAP_URL="$2"; shift 2 ;;
    --4dhumans-url)    FOURDH_URL="$2"; shift 2 ;;
    --branch)          BRANCH="$2"; shift 2 ;;
    -h|--help)         sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "$FORK_OWNER" ]]; then
  [[ -z "$EASYMOCAP_URL" ]] && EASYMOCAP_URL="https://github.com/$FORK_OWNER/EasyMocap.git"
  [[ -z "$FOURDH_URL"   ]] && FOURDH_URL="https://github.com/$FORK_OWNER/4D-Humans.git"
fi

# ---------------------------------------------------------------------------

check_one() {
  local path="$1"
  local url; url=$(git config --file .gitmodules --get "submodule.$path.url")
  local sha; sha=$(git rev-parse "HEAD:$path" 2>/dev/null || echo "")

  if [[ -z "$sha" ]]; then
    echo "  $path: no gitlink recorded — skipping"
    return 0
  fi

  printf '  %-22s %s\n' "$path" "$sha"
  printf '  %-22s %s\n' "  recorded remote" "$url"

  if git ls-remote "$url" 2>/dev/null | grep -q "$sha"; then
    echo "    OK — this commit is fetchable from the recorded remote."
    return 0
  fi

  echo "    UNFETCHABLE — this commit is not on $url."
  echo "    A recursive clone of this repository WILL FAIL for everyone."

  local dirty; dirty=$(git -C "$path" status --porcelain 2>/dev/null | wc -l)
  [[ "$dirty" -gt 0 ]] && echo "    plus $dirty uncommitted file(s) inside the submodule"
  return 1
}

echo "Checking submodule pointers..."
echo
status=0
check_one "backend/EasyMocap"  || status=1
echo
check_one "backend/4D-Humans"  || status=1
echo

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  [[ "$status" -eq 0 ]] && echo "All submodule commits are fetchable." \
                        || echo "Run without --check, passing fork URLs, to fix."
  exit "$status"
fi

if [[ "$status" -eq 0 ]]; then
  echo "Nothing to rescue — every recorded commit is already on its remote."
  exit 0
fi

if [[ -z "$EASYMOCAP_URL" || -z "$FOURDH_URL" ]]; then
  cat <<'MSG'
Fork URLs are required to proceed.

  1. Fork both repositories to an account you control:
       https://github.com/zju3dv/EasyMocap        -> your fork
       https://github.com/shubham-goel/4D-Humans  -> your fork

     Or, with the GitHub CLI:
       gh repo fork zju3dv/EasyMocap       --clone=false
       gh repo fork shubham-goel/4D-Humans --clone=false

  2. Re-run with:
       ./scripts/rescue-submodules.sh --fork-owner <your-github-username>

Forking EasyMocap is compatible with its licence: it permits redistribution for
research and non-profit use, and requires modifications stay open-source. Keep
the fork public and do not relicense it.
MSG
  exit 2
fi

echo "About to push local submodule commits to forks you control:"
echo "  backend/EasyMocap  -> $EASYMOCAP_URL  (branch: $BRANCH)"
echo "  backend/4D-Humans  -> $FOURDH_URL  (branch: $BRANCH)"
echo "and then rewrite .gitmodules to point at them."
echo
read -r -p "Proceed? [y/N] " reply
[[ "$reply" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

rescue_one() {
  local path="$1" fork_url="$2"
  echo
  echo "=== $path ==="

  local dirty; dirty=$(git -C "$path" status --porcelain | wc -l)
  if [[ "$dirty" -gt 0 ]]; then
    echo "  $dirty uncommitted file(s) — committing them first."
    git -C "$path" add -A
    git -C "$path" commit -m "rvectr: local working changes" || true
  fi

  if git -C "$path" remote | grep -qx fork; then
    git -C "$path" remote set-url fork "$fork_url"
  else
    git -C "$path" remote add fork "$fork_url"
  fi

  echo "  pushing $BRANCH -> fork"
  git -C "$path" push -u fork "HEAD:refs/heads/$BRANCH"

  git config --file .gitmodules "submodule.$path.url"    "$fork_url"
  git config --file .gitmodules "submodule.$path.branch" "$BRANCH"
  echo "  .gitmodules now points at $fork_url ($BRANCH)"
}

rescue_one "backend/EasyMocap" "$EASYMOCAP_URL"
rescue_one "backend/4D-Humans" "$FOURDH_URL"

git submodule sync --recursive

echo
echo "Done. Now verify, then commit .gitmodules:"
echo "    ./scripts/rescue-submodules.sh --check"
echo "    git add .gitmodules backend/EasyMocap backend/4D-Humans"
echo "    git commit -m 'fix: point submodules at pushable forks'"
echo
echo "Confirm a clean recursive clone succeeds before trusting this:"
echo "    git clone --recursive <this-repo-url> /tmp/rvectr-clone-test"
