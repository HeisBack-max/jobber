"""Gig/project-work collector interface (spec §19/§20).

Mirrors jobintel.collectors.base.JobSource but returns gig-specific
fields (rate, weekly hours, duration) that don't apply to salaried
employment. Kept as a separate interface so a comparable platform (RLHF
marketplace, expert network, etc.) can be added later without touching
the career-opportunity collectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from jobintel.models.schemas import RawJob


@dataclass
class RawGigDetails:
    raw_job: RawJob
    description_text: str
    hourly_rate_min: float | None = None
    hourly_rate_max: float | None = None
    rate_currency: str | None = None
    weekly_hours_min: float | None = None
    weekly_hours_max: float | None = None
    project_duration: str | None = None
    residency_countries: list[str] | None = None
    qualification_requirements: list[str] | None = None


class GigSource(ABC):
    name: str
    platform_reliability: float = 0.7  # 0-1, curated per platform (spec §20)

    @abstractmethod
    async def discover(self) -> list[RawJob]:
        """Return lightweight identity records for currently listed gigs."""

    @abstractmethod
    async def fetch_details(self, job: RawJob) -> RawGigDetails:
        """Return full gig detail including rate/hours/residency."""
