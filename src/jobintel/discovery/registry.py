"""Builds JobSource instances from config/sources.yaml.

Kept deliberately separate from config/strategic_companies.yaml: the
strategic registry is the *aspirational* watchlist (spec §15/§31),
this module builds only what can actually be collected today.

Adding an employer is a config change, never a code change, as long as
its ATS already has an adapter here. Per-source knobs (Lever EU region,
Workday page budget, career-site query terms) go in an `options:` map on
the company entry rather than being hard-coded per company.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jobintel.collectors.ashby import AshbySource
from jobintel.collectors.base import JobSource
from jobintel.collectors.careersite import AmazonJobsSource, GoogleCareersSource, MicrosoftCareersSource
from jobintel.collectors.greenhouse import GreenhouseSource
from jobintel.collectors.lever import LeverSource
from jobintel.collectors.recruitee import RecruiteeSource
from jobintel.collectors.smartrecruiters import SmartRecruitersSource
from jobintel.collectors.workable import WorkableSource
from jobintel.collectors.workday import WorkdaySource
from jobintel.settings import load_sources

# ats key -> (company_name, board_token, options) -> JobSource
_ADAPTER_BUILDERS: dict[str, Callable[[str, str, dict[str, Any]], JobSource]] = {
    "greenhouse": lambda name, token, opts: GreenhouseSource(name, token),
    "lever": lambda name, token, opts: LeverSource(name, token, region=opts.get("region", "global")),
    "ashby": lambda name, token, opts: AshbySource(name, token),
    "workday": lambda name, token, opts: WorkdaySource(name, token, **_pick(opts, "max_jobs")),
    "smartrecruiters": lambda name, token, opts: SmartRecruitersSource(name, token, **_pick(opts, "max_jobs")),
    "workable": lambda name, token, opts: WorkableSource(name, token),
    "recruitee": lambda name, token, opts: RecruiteeSource(name, token),
    # Career-site collectors are singletons per employer: the "board
    # token" is the employer key itself, and what varies is which search
    # terms to ask for (see collectors/careersite.py).
    "careersite_microsoft": lambda name, token, opts: MicrosoftCareersSource(name, **_pick(opts, "queries", "results_per_query")),
    "careersite_amazon": lambda name, token, opts: AmazonJobsSource(name, **_pick(opts, "queries", "results_per_query")),
    "careersite_google": lambda name, token, opts: GoogleCareersSource(name, **_pick(opts, "queries", "results_per_query")),
}

SUPPORTED_ATS = sorted(_ADAPTER_BUILDERS)


def _pick(options: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {k: options[k] for k in keys if k in options}


@dataclass
class RegistryEntry:
    name: str
    ats: str
    board_token: str
    collection_status: str
    strategic_themes: list[str]
    verification_status: str
    career_url: str | None
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def is_polled(self) -> bool:
        """Muted entries ship with an adapter but are not collected until
        `jobintel verify-boards` confirms the token resolves - the
        registry never claims coverage it hasn't proven."""
        return self.collection_status != "muted"


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
                options=company.get("options") or {},
            )
        )
    return entries


def build_source_for(ats: str, name: str, board_token: str, options: dict[str, Any] | None = None) -> JobSource | None:
    builder = _ADAPTER_BUILDERS.get(ats)
    return builder(name, board_token, options or {}) if builder else None


def build_sources(include_search_discovery: bool = True) -> list[JobSource]:
    """Build a live JobSource for every non-muted, non-blacklisted company
    in config/sources.yaml that declares a known ATS + board token, plus
    any search-discovery backend enabled in config/search_queries.yaml."""
    sources: list[JobSource] = []
    for entry in load_registry_entries():
        if not entry.is_polled:
            continue
        source = build_source_for(entry.ats, entry.name, entry.board_token, entry.options)
        if source is not None:
            sources.append(source)

    if include_search_discovery:
        from jobintel.discovery.search import build_search_sources

        sources.extend(build_search_sources())

    # Manually-entered gigs are collected on every run so a project
    # pasted into config/manual_gigs.yaml is scored and tracked like any
    # other opportunity. Costs nothing when the file is empty.
    from jobintel.gigs.manual import ManualGigSource

    manual = ManualGigSource()
    if manual.has_entries():
        sources.append(manual)
    return sources
