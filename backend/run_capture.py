#!/usr/bin/env python3
"""Compatibility entry point; prefer `uv run --frozen rvectr ...`."""
from rvectr.cli import main
if __name__=='__main__':
    raise SystemExit(main())
