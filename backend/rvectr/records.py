from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np


def clean_json(value):
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(clean_json(value), indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocate_run(root):
    """Atomic allocation; failed/partial runs are retained and never reused."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    versions = [int(m.group(1)) for p in root.iterdir()
                if (m := re.fullmatch(r"V1\.1\.(\d+)", p.name, re.IGNORECASE))]
    number = max([0] + versions) + 1
    while True:
        run = root / f"V1.1.{number}"
        try:
            run.mkdir()
            return run
        except FileExistsError:
            number += 1


def utc_now():
    return datetime.now(timezone.utc).isoformat()
