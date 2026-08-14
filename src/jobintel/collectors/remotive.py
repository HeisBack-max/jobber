"""Remotive public job board API adapter.

Verified endpoint (see https://remotive.com/api-documentation):
    GET https://remotive.com/api/remote-jobs?search={query}&limit={limit}
Unauthenticated. Unlike the ATS adapters, Remotive is a multi-employer
aggregator: each listing carries its own company_name rather than one
company per source, and the listing payload already contains the full
description and (when disclosed) a free-text salary string, so
fetch_details() is overridden to avoid a second request per job.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

BASE_URL = "https://remotive.com/api/remote-jobs"
DEFAULT_LIMIT = 100


class RemotiveSource(JobSource):
    """One instance per saved search. `search_query` is free text passed to
    Remotive's own `search` param (e.g. "cybersecurity", "AI training");
    an empty string collects Remotive's newest listings unfiltered."""

    def __init__(self, label: str, search_query: str = ""):
        slug = search_query.strip().lower().replace(" ", "-") or "all"
        self.name = f"remotive:{slug}"
        self.label = label
        self.search_query = search_query.strip()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        params: dict[str, str | int] = {"limit": DEFAULT_LIMIT}
        if self.search_query:
            params["search"] = self.search_query

        async with build_http_client() as client:
            try:
                resp = await client.get(BASE_URL, params=params)
            except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: endpoint not found (404) - reverify Remotive API URL")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            payload = resp.json()

        jobs = payload.get("jobs", [])
        raw_jobs: list[RawJob] = []
        for job in jobs:
            published_at = _parse_dt(job.get("publication_date"))
            raw_jobs.append(
                RawJob(
                    source="remotive",
                    source_job_id=str(job["id"]),
                    source_url=job.get("url", ""),
                    company_name=job.get("company_name") or "Unknown",
                    job_title=job.get("title", ""),
                    location_raw=job.get("candidate_required_location"),
                    updated_at=published_at,
                    collection_method=CollectionMethod.API,
                    raw_payload=job,
                )
            )
        logger.info("remotive.discover", search=self.search_query or "(none)", count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        return RawJobDetails(
            raw_job=job,
            description_html=payload.get("description"),
            salary_raw=(payload.get("salary") or "").strip() or None,
            published_at=_parse_dt(payload.get("publication_date")),
            raw_payload=payload,
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
