"""Builds JobSource instances from config/sources.yaml.

Kept deliberately separate from config/strategic_companies.yaml: the
strategic registry is the *aspirational* watchlist (spec §15/§31),
this module builds only what can actually be collected today.
"""

from __future__ import annotations

from dataclasses import dataclass

from jobintel.collectors.ashby import AshbySource
from jobintel.collectors.base import JobSource
from jobintel.collectors.greenhouse import GreenhouseSource
from jobintel.collectors.lever import LeverSource
from jobintel.settings import load_sources

_ADAPTER_BUILDERS = {
    "greenhouse": lambda name, token: GreenhouseSource(name, token),
    "lever": lambda name, token: LeverSource(name, token),
    "ashby": lambda name, token: AshbySource(name, token),
}


@dataclass
class RegistryEntry:
    name: str
    ats: str
    board_token: str
    collection_status: str
    strategic_themes: list[str]
    verification_status: str
    career_url: str | None


def load_registry_entries() -> list[RegistryEntry]:
    data = load_sources()
    entries = []
    for company in data.get("companies", []):
        if company.get("collection_status") == "blacklisted":
            continue
        if not company.get("ats") or not company.get("board_token"):
            continue
        entries.append(
            RegistryEntry(
                name=company["name"],
                ats=company["ats"],
                board_token=company["board_token"],
                collection_status=company.get("collection_status", "normal"),
                strategic_themes=company.get("strategic_themes", []),
                verification_status=company.get("verification_status", "UNVERIFIED"),
                career_url=company.get("career_url"),
            )
        )
    return entries


def build_source_for(ats: str, name: str, board_token: str) -> JobSource | None:
    builder = _ADAPTER_BUILDERS.get(ats)
    return builder(name, board_token) if builder else None


def build_sources() -> list[JobSource]:
    """Build a live JobSource for every muted/blacklisted-excluded company
    in config/sources.yaml that declares a known ATS + board token."""
    sources: list[JobSource] = []
    for entry in load_registry_entries():
        if entry.collection_status == "muted":
            continue
        builder = _ADAPTER_BUILDERS.get(entry.ats)
        if builder is None:
            continue
        sources.append(builder(entry.name, entry.board_token))
    return sources
