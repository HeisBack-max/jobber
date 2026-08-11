"""Lever Postings public API adapter.

Verified endpoint (see ARCHITECTURE.md §6):
    GET https://api.lever.co/v0/postings/{site}?mode=json
(EU tenants: https://api.eu.lever.co/v0/postings/{site}?mode=json)
Unauthenticated; only `published`-state postings are returned.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob

logger = structlog.get_logger()

BASE_URL_GLOBAL = "https://api.lever.co/v0/postings/{site}"
BASE_URL_EU = "https://api.eu.lever.co/v0/postings/{site}"


class LeverSource(JobSource):
    def __init__(self, company_name: str, site: str, region: str = "global"):
        self.name = f"lever:{site}"
        self.company_name = company_name
        self.site = site
        self.base_url = (BASE_URL_EU if region == "eu" else BASE_URL_GLOBAL).format(site=site)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        async with build_http_client() as client:
            try:
                resp = await client.get(self.base_url, params={"mode": "json"})
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: site not found (404) - reverify site name")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            postings = resp.json()

        raw_jobs: list[RawJob] = []
        for posting in postings:
            created_at = _epoch_ms_to_dt(posting.get("createdAt"))
            categories = posting.get("categories") or {}
            location = categories.get("location") or posting.get("country")
            raw_jobs.append(
                RawJob(
                    source="lever",
                    source_job_id=str(posting["id"]),
                    source_url=posting.get("hostedUrl", ""),
                    company_name=self.company_name,
                    job_title=posting.get("text", ""),
                    location_raw=location,
                    updated_at=created_at,
                    collection_method=CollectionMethod.ATS,
                    raw_payload=posting,
                )
            )
        logger.info("lever.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs


def _epoch_ms_to_dt(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (ValueError, OSError, OverflowError):
        return None
