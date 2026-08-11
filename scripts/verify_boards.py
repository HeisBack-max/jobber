#!/usr/bin/env python3
"""Live-checks every (ats, board_token) pair in config/sources.yaml so a
stale/renamed token is caught explicitly rather than silently reading as
"zero current vacancies" (see ARCHITECTURE.md §6, IMPLEMENTATION_PLAN.md §6.1).

Usage:
    python scripts/verify_boards.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.collectors.base import SourceError  # noqa: E402
from jobintel.discovery.registry import build_source_for, load_registry_entries  # noqa: E402


async def verify_all() -> list[tuple[str, str, bool, str]]:
    results = []
    for entry in load_registry_entries():
        source = build_source_for(entry.ats, entry.name, entry.board_token)
        if source is None:
            results.append((entry.name, entry.ats, False, "no adapter implemented for this ATS"))
            continue
        try:
            jobs = await source.discover()
            results.append((entry.name, entry.ats, True, f"OK - {len(jobs)} jobs live"))
        except SourceError as exc:
            results.append((entry.name, entry.ats, False, str(exc)))
        except Exception as exc:  # noqa: BLE001
            results.append((entry.name, entry.ats, False, f"unexpected error: {exc}"))

    print(f"{'Company':<25} {'ATS':<12} {'Status':<8} Detail")
    print("-" * 90)
    for name, ats, ok, detail in results:
        print(f"{name:<25} {ats:<12} {'OK' if ok else 'FAIL':<8} {detail}")
    return results


if __name__ == "__main__":
    asyncio.run(verify_all())
