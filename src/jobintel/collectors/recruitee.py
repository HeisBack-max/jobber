"""Recruitee public careers API adapter (unauthenticated).

    GET https://{company}.recruitee.com/api/offers/
    ->  {"offers": [{"id", "title", "slug", "description", "requirements",
         "location", "city", "country_code", "careers_url",
         "careers_apply_url", "published_at", "employment_type_code",
         "remote": bool, "min_hours", "max_hours"}, ...]}

The listing response includes the full description, so no per-job
request is needed.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

BASE_URL = "https://{company}.recruitee.com/api/offers/"


class RecruiteeSource(JobSource):
    def __init__(self, company_name: str, subdomain: str):
        self.name = f"recruitee:{subdomain}"
        self.company_name = company_name
        self.subdomain = subdomain

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        url = BASE_URL.format(company=self.subdomain)
        async with build_http_client() as client:
            try:
                resp = await client.get(url)
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: request failed: {exc}") from exc

            if resp.status_code == 404:
                raise SourceError(f"{self.name}: company not found (404) - reverify subdomain")
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

            payload = resp.json()

        raw_jobs: list[RawJob] = []
        for offer in payload.get("offers", []):
            raw_jobs.append(
                RawJob(
                    source="recruitee",
                    source_job_id=str(offer.get("id", "")),
                    source_url=offer.get("careers_url") or offer.get("careers_apply_url", ""),
                    company_name=self.company_name,
                    job_title=offer.get("title", ""),
                    location_raw=_format_location(offer),
                    updated_at=_parse_dt(offer.get("published_at")),
                    collection_method=CollectionMethod.ATS,
                    raw_payload=offer,
                )
            )
        logger.info("recruitee.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        parts = [payload.get("description"), payload.get("requirements")]
        return RawJobDetails(
            raw_job=job,
            description_html="\n".join(p for p in parts if p) or None,
            published_at=_parse_dt(payload.get("published_at")) or job.updated_at,
            raw_payload=payload,
        )


def _format_location(offer: dict) -> str | None:
    text = offer.get("location") or ", ".join(
        p for p in [offer.get("city"), offer.get("country_code")] if p
    )
    if offer.get("remote"):
        text = f"Remote{' - ' + text if text else ''}"
    return text or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
