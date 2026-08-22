"""SmartRecruiters Posting API adapter (unauthenticated public endpoints).

    GET https://api.smartrecruiters.com/v1/companies/{identifier}/postings?limit=100&offset=0
    ->  {"totalFound": n, "content": [{"id", "name", "location": {...},
         "releasedDate", "typeOfEmployment": {"label"}, "ref"}, ...]}

    GET https://api.smartrecruiters.com/v1/companies/{identifier}/postings/{id}
    ->  {"jobAd": {"sections": {"companyDescription": {"text"},
         "jobDescription": {"text"}, "qualifications": {"text"},
         "additionalInformation": {"text"}}}, "applyUrl", ...}

The listing response carries no description, so details are fetched per
job (bounded by `max_jobs`).
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

BASE_URL = "https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
PAGE_SIZE = 100
DEFAULT_MAX_JOBS = 300

_SECTION_ORDER = ("companyDescription", "jobDescription", "qualifications", "additionalInformation")


class SmartRecruitersSource(JobSource):
    def __init__(self, company_name: str, identifier: str, max_jobs: int = DEFAULT_MAX_JOBS):
        self.name = f"smartrecruiters:{identifier}"
        self.company_name = company_name
        self.identifier = identifier
        self.max_jobs = max_jobs
        self.base_url = BASE_URL.format(identifier=identifier)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        raw_jobs: list[RawJob] = []
        async with build_http_client() as client:
            offset = 0
            while offset < self.max_jobs:
                try:
                    resp = await client.get(self.base_url, params={"limit": PAGE_SIZE, "offset": offset})
                except Exception as exc:  # noqa: BLE001
                    raise SourceError(f"{self.name}: request failed: {exc}") from exc

                if resp.status_code == 404:
                    raise SourceError(f"{self.name}: company identifier not found (404) - reverify board_token")
                if resp.status_code != 200:
                    raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

                payload = resp.json()
                postings = payload.get("content", [])
                if not postings:
                    break

                for posting in postings:
                    raw_jobs.append(
                        RawJob(
                            source="smartrecruiters",
                            source_job_id=str(posting.get("id") or posting.get("uuid", "")),
                            source_url=_posting_url(posting, self.identifier),
                            company_name=self.company_name,
                            job_title=posting.get("name", ""),
                            location_raw=_format_location(posting.get("location")),
                            updated_at=_parse_dt(posting.get("releasedDate")),
                            collection_method=CollectionMethod.ATS,
                            raw_payload=posting,
                        )
                    )

                offset += PAGE_SIZE
                if offset >= int(payload.get("totalFound", 0)):
                    break

        logger.info("smartrecruiters.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        async with build_http_client() as client:
            try:
                resp = await client.get(f"{self.base_url}/{job.source_job_id}")
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: detail request failed: {exc}") from exc
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: detail request returned {resp.status_code}")
            payload = resp.json()

        sections = ((payload.get("jobAd") or {}).get("sections") or {})
        description_html = "\n".join(
            f"<h3>{sections[name].get('title', name)}</h3>{sections[name].get('text', '')}"
            for name in _SECTION_ORDER
            if isinstance(sections.get(name), dict)
        )
        return RawJobDetails(
            raw_job=job,
            description_html=description_html or None,
            published_at=_parse_dt(payload.get("releasedDate")) or job.updated_at,
            raw_payload=payload,
        )


def _posting_url(posting: dict, identifier: str) -> str:
    return (
        posting.get("applyUrl")
        or posting.get("postingUrl")
        or f"https://jobs.smartrecruiters.com/{identifier}/{posting.get('id', '')}"
    )


def _format_location(location: dict | None) -> str | None:
    if not location:
        return None
    parts = [location.get("city"), location.get("region"), location.get("country")]
    text = ", ".join(p for p in parts if p)
    if location.get("remote"):
        # SmartRecruiters exposes remoteness as a boolean field rather
        # than in the location string; surface it so the geography
        # classifier sees it (it only reads location_raw + description).
        text = f"Remote{' - ' + text if text else ''}"
    return text or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
