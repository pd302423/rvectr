"""The pre-push hook must pick a comparison base even when the old remote tip is not in this checkout."""
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".githooks" / "pre-push"
ZERO = "0" * 40


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """main has commit A; a feature branch adds B and C. The publish check is replaced by a stub that records its arguments."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Local Test")
    git(tmp_path, "config", "user.email", "local@example.invalid")
    commits = {}
    for name in ("A", "B", "C"):
        if name == "B":
            git(tmp_path, "switch", "-c", "feature")
        (tmp_path / "file.txt").write_text(name)
        git(tmp_path, "add", "file.txt")
        git(tmp_path, "commit", "-m", name)
        commits[name] = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check_publish.py").write_text(
        "import sys\nopen('calls.txt', 'a').write(' '.join(sys.argv[1:]) + '\\n')\n")
    return tmp_path, commits


def push(root, tip, old):
    return subprocess.run(["sh", str(HOOK), "origin", "url"], cwd=root, capture_output=True, text=True,
                          input=f"refs/heads/feature {tip} refs/heads/feature {old}\n")


@pytest.mark.parametrize("old, expected_base", [
    ("known", "B"),         # normal push: compare with the old remote tip
    (ZERO, "A"),            # new branch: compare with main
    ("1234567890" * 4, "A"),   # force-push over a tip this checkout never fetched: compare with main
])
def test_hook_chooses_a_base_for_normal_new_and_unfetched_old_tips(repo, old, expected_base):
    root, commits = repo
    old = commits["B"] if old == "known" else old
    done = push(root, commits["C"], old)
    assert done.returncode == 0, done.stderr
    assert (root / "calls.txt").read_text().strip() == (
        f"--commits-only --base {commits[expected_base]} --tip {commits['C']}")
    assert "Not a valid commit name" not in done.stderr


def test_hook_stops_with_a_message_when_there_is_no_main_to_compare_with(repo):
    root, commits = repo
    git(root, "branch", "-m", "main", "trunk")      # no refs/heads/main left
    done = push(root, commits["C"], "1234567890" * 4)
    assert done.returncode == 2 and "No shared main base" in done.stderr
    assert not (root / "calls.txt").exists()
