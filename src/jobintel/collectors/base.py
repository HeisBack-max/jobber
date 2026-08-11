"""Common interface every collector adapter implements (spec §29)."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from jobintel.models.schemas import RawJob, RawJobDetails
from jobintel.settings import get_settings


class JobSource(ABC):
    """One instance per company/board. Adapters must not bypass auth,
    CAPTCHAs, paywalls, or anti-bot protections, and must use the shared
    rate-limited HTTP client below rather than rolling their own.
    """

    name: str

    @abstractmethod
    async def discover(self) -> list[RawJob]:
        """Return lightweight identity records for currently listed jobs."""

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        """Default: the discover() payload already contains full details.

        Adapters whose listing endpoint returns full descriptions (Lever,
        Ashby) override nothing here; adapters that need a second request
        per job (Greenhouse without ?content=true) override this method.
        """
        return RawJobDetails(raw_job=job, raw_payload=job.raw_payload)


def build_http_client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )


class SourceError(Exception):
    """Raised by a collector on an unrecoverable per-source failure.

    Caught at the orchestration layer so one broken source never aborts
    the whole run (spec §57).
    """
