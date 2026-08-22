"""Workable public job-widget API adapter (unauthenticated).

    GET https://apply.workable.com/api/v1/widget/accounts/{subdomain}?details=true
    ->  {"name": "...", "jobs": [{"title", "shortcode", "url",
         "application_url", "employment_type", "telecommuting": bool,
         "country", "city", "state", "published_on", "created_at",
         "description", "requirements", "benefits"}, ...]}

`details=true` returns the full description in the listing response, so
no per-job request is needed.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

BASE_URL = "https://apply.workable.com/api/v1/widget/accounts/{subdomain}"


class WorkableSource(JobSource):
    def __init__(self, company_name: str, subdomain: str):
        self.name = f"workable:{subdomain}"
        self.company_name = company_name
        self.subdomain = subdomain

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        url = BASE_URL.format(subdomain=self.subdomain)
        async with build_http_client() as client:
            try:
                resp = await client.get(url, params={"details": "true"})
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: account not found (404) - reverify subdomain")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            payload = resp.json()

        raw_jobs: list[RawJob] = []
        for job in payload.get("jobs", []):
            raw_jobs.append(
                RawJob(
                    source="workable",
                    source_job_id=str(job.get("shortcode") or job.get("id", "")),
                    source_url=job.get("url") or job.get("application_url", ""),
                    company_name=self.company_name,
                    job_title=job.get("title", ""),
                    location_raw=_format_location(job),
                    updated_at=_parse_dt(job.get("published_on") or job.get("created_at")),
                    collection_method=CollectionMethod.ATS,
                    raw_payload=job,
                )
            )
        logger.info("workable.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        parts = [payload.get("description"), payload.get("requirements"), payload.get("benefits")]
        return RawJobDetails(
            raw_job=job,
            description_html="\n".join(p for p in parts if p) or None,
            published_at=_parse_dt(payload.get("published_on")) or job.updated_at,
            raw_payload=payload,
        )


def _format_location(job: dict) -> str | None:
    parts = [job.get("city"), job.get("state"), job.get("country")]
    text = ", ".join(p for p in parts if p)
    if job.get("telecommuting"):
        # Workable's `telecommuting` boolean is the only remote signal on
        # many postings whose location string is just the HQ city.
        text = f"Remote{' - ' + text if text else ''}"
    return text or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
