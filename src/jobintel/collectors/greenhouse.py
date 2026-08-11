"""Greenhouse Job Board public API adapter.

Verified endpoint (see ARCHITECTURE.md §6):
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
No authentication required for GET; this adapter never calls the
(auth-required) application-submission endpoint.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob

logger = structlog.get_logger()

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseSource(JobSource):
    def __init__(self, company_name: str, board_token: str):
        self.name = f"greenhouse:{board_token}"
        self.company_name = company_name
        self.board_token = board_token

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        url = BASE_URL.format(token=self.board_token)
        async with build_http_client() as client:
            try:
                resp = await client.get(url, params={"content": "true"})
            except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: board token not found (404) - reverify token")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            payload = resp.json()

        jobs = payload.get("jobs", [])
        raw_jobs: list[RawJob] = []
        for job in jobs:
            updated_at = _parse_dt(job.get("updated_at"))
            location = (job.get("location") or {}).get("name")
            raw_jobs.append(
                RawJob(
                    source="greenhouse",
                    source_job_id=str(job["id"]),
                    source_url=job.get("absolute_url", ""),
                    company_name=self.company_name,
                    job_title=job.get("title", ""),
                    location_raw=location,
                    updated_at=updated_at,
                    collection_method=CollectionMethod.ATS,
                    raw_payload=job,
                )
            )
        logger.info("greenhouse.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
