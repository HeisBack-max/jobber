"""Surfaces strategic-company collection coverage honestly (spec §15-18).

Rather than silently having "no coverage" for OpenAI/Google/Microsoft/etc,
this module lets the dashboard's source-health view show exactly which
strategic targets have a live collector today vs. which are
registry-only and why (see IMPLEMENTATION_PLAN.md §1).
"""

from __future__ import annotations

from dataclasses import dataclass

from jobintel.settings import load_strategic_companies


@dataclass
class StrategicCoverage:
    name: str
    tier: str
    watch_priority: str
    strategic_themes: list[str]
    ats: str | None
    verification_status: str
    notes: str | None
    has_live_collector: bool


def get_strategic_coverage() -> list[StrategicCoverage]:
    data = load_strategic_companies()
    coverage: list[StrategicCoverage] = []
    for tier_name, tier in data.get("tiers", {}).items():
        default_status = tier.get("all_verification_status")
        for company in tier.get("companies", []):
            ats = company.get("ats")
            token = company.get("board_token")
            status = company.get("verification_status", default_status or "UNVERIFIED")
            coverage.append(StrategicCoverage(
                name=company["name"],
                tier=tier_name,
                watch_priority=company.get("watch_priority", tier_name),
                strategic_themes=company.get("strategic_themes", []),
                ats=ats,
                verification_status=status,
                notes=company.get("notes"),
                has_live_collector=bool(ats and token),
            ))
    return coverage
