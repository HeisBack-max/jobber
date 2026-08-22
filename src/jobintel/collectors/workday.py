"""Workday CXS (career-site experience) public API adapter.

Workday is the ATS behind most large enterprises that do *not* run a
public Greenhouse/Lever/Ashby board (NVIDIA, Salesforce, ServiceNow,
AMD, ...), so this adapter is what closes that coverage gap for the
strategic watchlist (IMPLEMENTATION_PLAN.md §1).

Endpoint shape (unauthenticated, the same requests the public careers
page itself issues):

    POST https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
         {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    ->   {"total": 1234, "jobPostings": [{"title", "externalPath",
          "locationsText", "postedOn", "bulletFields": ["JR123"]}, ...]}

    GET  https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{externalPath}
    ->   {"jobPostingInfo": {"jobDescription": "<html>", "startDate",
          "location", "timeType", "remoteType", "externalUrl"}}

Unlike Greenhouse/Lever/Ashby, the listing response carries no
description, so `fetch_details()` really does issue one request per job
(bounded by `max_jobs`, since a single Workday tenant can list tens of
thousands of postings and Richard's pipeline is signal-over-volume).

`board_token` format used in config/sources.yaml:

    "{tenant}.{host}/{site}"      e.g. "nvidia.wd5/NVIDIAExternalCareerSite"

A full careers URL is also accepted and parsed into the same triple, so
a token can be copied straight out of the browser address bar.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails

logger = structlog.get_logger()

PAGE_SIZE = 20  # Workday rejects limit > 20 on the CXS endpoint.
DEFAULT_MAX_JOBS = 200

_TOKEN_RE = re.compile(r"^(?P<tenant>[^.\s/]+)\.(?P<host>wd\d+)/(?P<site>[^/\s]+)$")
_URL_RE = re.compile(
    r"https?://(?P<tenant>[^.]+)\.(?P<host>wd\d+)\.myworkdayjobs\.com/"
    r"(?:wday/cxs/(?P=tenant)/)?(?:[a-z]{2}-[A-Z]{2}/)?(?P<site>[^/?#]+)"
)

# "Posted 30+ Days Ago" / "Posted Yesterday" / "Posted Today" - Workday
# returns a human string here, not a date, so this is best-effort and
# deliberately conservative: an unparseable value stays None (unknown
# publication date) rather than being guessed as "now", which would
# inflate the freshness score of an old posting.
_POSTED_DAYS_RE = re.compile(r"(\d+)\+?\s*day", re.I)


class WorkdaySource(JobSource):
    def __init__(self, company_name: str, board_token: str, max_jobs: int = DEFAULT_MAX_JOBS):
        tenant, host, site = parse_workday_token(board_token)
        self.name = f"workday:{tenant}/{site}"
        self.company_name = company_name
        self.tenant = tenant
        self.host = host
        self.site = site
        self.max_jobs = max_jobs
        self.base_url = f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"

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
                    resp = await client.post(
                        f"{self.base_url}/jobs",
                        json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                    )
                except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                    raise SourceError(f"{self.name}: request failed: {exc}") from exc

                if resp.status_code == 404:
                    raise SourceError(f"{self.name}: tenant/site not found (404) - reverify board_token")
                if resp.status_code != 200:
                    raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

                payload = resp.json()
                postings = payload.get("jobPostings", [])
                if not postings:
                    break

                for posting in postings:
                    external_path = posting.get("externalPath", "")
                    raw_jobs.append(
                        RawJob(
                            source="workday",
                            source_job_id=_job_id(posting, external_path),
                            source_url=f"https://{self.tenant}.{self.host}.myworkdayjobs.com/{self.site}{external_path}",
                            company_name=self.company_name,
                            job_title=posting.get("title", ""),
                            location_raw=posting.get("locationsText"),
                            updated_at=_posted_on_to_dt(posting.get("postedOn")),
                            collection_method=CollectionMethod.ATS,
                            raw_payload={**posting, "_cxs_path": external_path},
                        )
                    )

                offset += PAGE_SIZE
                if offset >= int(payload.get("total", 0)):
                    break

        logger.info("workday.discover", company=self.company_name, count=len(raw_jobs))
        return raw_jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        """One request per job: the CXS listing endpoint returns no
        description at all, so unlike the other ATS adapters this really
        does need a second call (see module docstring)."""
        path = job.raw_payload.get("_cxs_path")
        if not path:
            return RawJobDetails(raw_job=job, raw_payload=job.raw_payload)

        async with build_http_client() as client:
            try:
                resp = await client.get(f"{self.base_url}{path}", headers={"Accept": "application/json"})
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: detail request failed: {exc}") from exc
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: detail request returned {resp.status_code}")
            payload = resp.json()

        info = payload.get("jobPostingInfo", {}) or {}
        location_parts = [info.get("location"), info.get("additionalLocations")]
        location = ", ".join(p for p in location_parts if isinstance(p, str) and p)
        remote_type = info.get("remoteType")
        # remoteType ("Remote", "Hybrid", "Flexible") is a first-class
        # Workday field the geography classifier would otherwise never
        # see, since it lives outside the description HTML.
        description_html = info.get("jobDescription") or ""
        if remote_type:
            description_html = f"<p>Workday remote type: {remote_type}.</p>{description_html}"

        return RawJobDetails(
            raw_job=job,
            description_html=description_html,
            published_at=_parse_iso(info.get("startDate")) or job.updated_at,
            application_deadline=_parse_iso(info.get("endDate")),
            raw_payload={**payload, "_location_resolved": location or job.location_raw},
        )


def parse_workday_token(token: str) -> tuple[str, str, str]:
    """Accepts "tenant.wd5/SiteName" or a full myworkdayjobs.com URL."""
    token = (token or "").strip()
    match = _TOKEN_RE.match(token)
    if match:
        return match.group("tenant"), match.group("host"), match.group("site")
    match = _URL_RE.match(token)
    if match:
        return match.group("tenant"), match.group("host"), match.group("site")
    raise SourceError(
        f"workday: unparseable board_token {token!r} - expected 'tenant.wd5/SiteName' "
        "or a full https://tenant.wd5.myworkdayjobs.com/SiteName URL"
    )


def _job_id(posting: dict, external_path: str) -> str:
    bullets = posting.get("bulletFields") or []
    if bullets and isinstance(bullets[0], str) and bullets[0].strip():
        return bullets[0].strip()
    return external_path.rsplit("/", 1)[-1] or external_path


def _posted_on_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    lowered = value.lower()
    if "today" in lowered:
        return datetime.now(UTC)
    if "yesterday" in lowered:
        return datetime.now(UTC) - timedelta(days=1)
    match = _POSTED_DAYS_RE.search(lowered)
    if match:
        return datetime.now(UTC) - timedelta(days=int(match.group(1)))
    return None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
