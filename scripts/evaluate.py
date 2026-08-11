#!/usr/bin/env python3
"""Thin wrapper: `python scripts/evaluate.py` == `jobintel evaluate`."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.pipeline import run_evaluation  # noqa: E402

if __name__ == "__main__":
    print(run_evaluation().render())
