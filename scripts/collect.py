#!/usr/bin/env python3
"""Thin wrapper: `python scripts/collect.py` == `jobintel collect`."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.pipeline import run_collection  # noqa: E402

if __name__ == "__main__":
    print(asyncio.run(run_collection()).render())
