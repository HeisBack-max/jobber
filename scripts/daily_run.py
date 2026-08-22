#!/usr/bin/env python3
"""Full daily pipeline for cron/system-scheduler use:

    0 6 * * * /path/to/.venv/bin/python /path/to/jobber/scripts/daily_run.py

Prints a run summary in the format described in spec §56 and exits 0
even if individual sources failed (failures are captured in the summary,
not raised) - a cron job should only alert on a hard crash of the whole
process, not on "one board was unreachable today".
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.digest.generator import generate_digest  # noqa: E402
from jobintel.notifications.dispatch import dispatch_notifications  # noqa: E402
from jobintel.pipeline import run_collection, run_evaluation  # noqa: E402


def main() -> None:
    started = time.monotonic()
    collect_summary = asyncio.run(run_collection())
    eval_summary = run_evaluation()
    digest = generate_digest()
    # No-op when no channel is configured, and a failing channel is
    # reported in the summary rather than raised - a cron job must not
    # exit non-zero because Telegram was briefly unreachable.
    notify_summary = asyncio.run(dispatch_notifications())
    duration = time.monotonic() - started

    print(collect_summary.render())
    print()
    print(eval_summary.render())
    print()
    print(digest.render_text())
    print()
    print(notify_summary.render())
    print(f"\nRun duration: {duration:.1f}s")


if __name__ == "__main__":
    main()
