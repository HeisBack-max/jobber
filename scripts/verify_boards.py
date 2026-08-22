#!/usr/bin/env python3
"""Live-checks every (ats, board_token) pair in config/sources.yaml so a
stale/renamed token is caught explicitly rather than silently reading as
"zero current vacancies" (see ARCHITECTURE.md §6, IMPLEMENTATION_PLAN.md §6.1).

Muted entries are checked too: muting is how a newly-added board ships
without being polled until it has been verified once, so the whole point
is that this command can confirm it.

Usage:
    python scripts/verify_boards.py            # check every configured board
    python scripts/verify_boards.py --muted    # check only the muted ones
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.collectors.base import SourceError  # noqa: E402
from jobintel.discovery.registry import build_source_for, load_registry_entries  # noqa: E402


@dataclass
class VerificationResult:
    name: str
    ats: str
    board_token: str
    polled: bool
    ok: bool
    detail: str

    # Kept for backwards compatibility with the original tuple-based
    # return value used by `jobintel verify-boards`.
    def __iter__(self):
        return iter((self.name, self.ats, self.ok, self.detail))


async def verify_all(muted_only: bool = False) -> list[VerificationResult]:
    entries = [e for e in load_registry_entries() if not muted_only or not e.is_polled]
    results: list[VerificationResult] = []

    async def check(entry) -> VerificationResult:
        source = build_source_for(entry.ats, entry.name, entry.board_token, entry.options)
        if source is None:
            return VerificationResult(entry.name, entry.ats, entry.board_token, entry.is_polled, False,
                                      "no adapter implemented for this ATS")
        try:
            jobs = await source.discover()
        except SourceError as exc:
            return VerificationResult(entry.name, entry.ats, entry.board_token, entry.is_polled, False, str(exc))
        except Exception as exc:  # noqa: BLE001
            return VerificationResult(entry.name, entry.ats, entry.board_token, entry.is_polled, False,
                                      f"unexpected error: {exc}")
        return VerificationResult(entry.name, entry.ats, entry.board_token, entry.is_polled, True,
                                  f"OK - {len(jobs)} jobs live")

    semaphore = asyncio.Semaphore(6)

    async def guarded(entry):
        async with semaphore:
            return await check(entry)

    results = list(await asyncio.gather(*[guarded(e) for e in entries]))

    print(f"{'Company':<25} {'ATS':<16} {'Polled':<8} {'Status':<8} Detail")
    print("-" * 100)
    for r in results:
        print(f"{r.name:<25} {r.ats:<16} {'yes' if r.polled else 'MUTED':<8} {'OK' if r.ok else 'FAIL':<8} {r.detail}")

    failures = [r for r in results if not r.ok]
    unverified_but_live = [r for r in results if r.ok and not r.polled]
    print(f"\n{len(results) - len(failures)}/{len(results)} boards reachable.")
    if unverified_but_live:
        print(
            "\nMuted but live - these are collecting nothing until unmuted. Set "
            "collection_status to `normal` (or higher) in config/sources.yaml for:"
        )
        for r in unverified_but_live:
            print(f"  - {r.name} ({r.ats}:{r.board_token}) - {r.detail}")
    if failures:
        print("\nFailing boards (fix the token or mark the entry blacklisted):")
        for r in failures:
            print(f"  - {r.name} ({r.ats}:{r.board_token}) - {r.detail}")
    return results


if __name__ == "__main__":
    asyncio.run(verify_all(muted_only="--muted" in sys.argv))
