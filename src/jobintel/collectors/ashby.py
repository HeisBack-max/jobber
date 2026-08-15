"""Ashby public Job Postings API adapter.

Verified endpoint (see ARCHITECTURE.md §6):
    GET https://api.ashbyhq.com/posting-api/job-board/{clientname}?includeCompensation=true
Unauthenticated; returns all currently published postings, no
server-side filtering.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{client}"


class AshbySource(JobSource):
    def __init__(self, company_name: str, client_name: str):
        self.name = f"ashby:{client_name}"
        self.company_name = company_name
        self.client_name = client_name

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        url = BASE_URL.format(client=self.client_name)
        async with build_http_client() as client:
            try:
                resp = await client.get(url, params={"includeCompensation": "true"})
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: client not found (404) - reverify client name")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            payload = resp.json()

        jobs = payload.get("jobs", [])
        raw_jobs: list[RawJob] = []
        for job in jobs:
            published_at = _parse_dt(job.get("publishedAt"))
            location = job.get("location")
            raw_jobs.append(
                RawJob(
                    source="ashby",
                    source_job_id=str(job["id"]),
                    source_url=job.get("jobUrl") or job.get("applyUrl", ""),
                    company_name=self.company_name,
                    job_title=job.get("title", ""),
                    location_raw=location,
                    updated_at=published_at,
                    collection_method=CollectionMethod.ATS,
                    raw_payload=job,
                )
            )
        logger.info("ashby.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        # The list response already includes full description and
        # (when requested) compensation per job - no second request needed.
        payload = job.raw_payload
        return RawJobDetails(
            raw_job=job,
            description_html=payload.get("descriptionHtml"),
            description_text=payload.get("descriptionPlain"),
            salary_raw=_format_compensation(payload.get("compensation")),
            published_at=_parse_dt(payload.get("publishedAt")) or job.updated_at,
            raw_payload=payload,
        )


def _format_compensation(compensation: dict | None) -> str | None:
    if not compensation:
        return None
    summary = compensation.get("compensationTierSummary") or compensation.get("scrapeableCompensationSalarySummary")
    if summary:
        return summary
    components = compensation.get("summaryComponents") or []
    parts = []
    for comp in components:
        lo, hi = comp.get("minValue"), comp.get("maxValue")
        currency = comp.get("currencyCode", "")
        if lo is not None or hi is not None:
            parts.append(f"{currency} {lo}-{hi}".strip())
    return "; ".join(parts) if parts else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
