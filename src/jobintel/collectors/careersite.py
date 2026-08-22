"""Career-site collectors for the strategic employers that run their own
ATS instead of Greenhouse/Lever/Ashby (IMPLEMENTATION_PLAN.md §1).

Each adapter calls the same public, unauthenticated JSON endpoint the
employer's own careers page calls from the browser. None of them bypass
authentication, CAPTCHAs, or anti-bot protection, and none parse HTML:
if an employer stops publishing a JSON search endpoint, the right answer
is a BROKEN source-health entry, not an HTML scraper (spec §65).

Because these endpoints are unversioned and undocumented, every adapter
validates the response *shape* before parsing it and raises SourceError
on anything unexpected. That turns an upstream API change into a loud
"BROKEN" row in the dashboard's Source Health tab rather than a silent
"0 jobs today", which is the failure mode that would quietly hide a
whole employer from Richard's feed.

Query-driven by design: these employers list tens of thousands of
postings, and collecting all of them would drown the pipeline. Each
adapter takes the search terms it should ask for - by default the ones
in config/search_queries.yaml (see `default_query_terms()`).
"""

from __future__ import annotations

from datetime import datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails
from jobintel.settings import load_search_queries

logger = structlog.get_logger()

DEFAULT_RESULTS_PER_QUERY = 20

# Fallback used only if config/search_queries.yaml has no `career_site_terms`
# block - keeps the adapters usable standalone (e.g. in tests).
_FALLBACK_TERMS = ["AI trainer", "technical trainer", "AI enablement", "cybersecurity training"]


def default_query_terms(limit: int = 8) -> list[str]:
    """Plain search terms derived from config/search_queries.yaml.

    The query families there are written for a search engine (quoted
    phrases plus "remote"); these employer APIs take a bare keyword
    string, so quotes and the "remote"/"jobs" noise words are stripped.
    """
    data = load_search_queries()
    explicit = data.get("career_site_terms")
    if explicit:
        return list(explicit)[:limit]

    terms: list[str] = []
    for family in data.get("query_families", {}).values():
        for query in family.get("queries", []):
            cleaned = query.replace('"', " ")
            cleaned = " ".join(w for w in cleaned.split() if w.lower() not in {"remote", "jobs", "freelance", "contract"})
            cleaned = cleaned.strip()
            if cleaned and cleaned not in terms:
                terms.append(cleaned)
    return terms[:limit] or list(_FALLBACK_TERMS)


class _QueryDrivenSource(JobSource):
    """Shared plumbing: run N search queries, de-duplicate by job id."""

    source_key: str
    # The employer's own careers system - the most authoritative source
    # there is for that employer's vacancies.
    source_type = "official_employer"
    quality_rank = 1

    def __init__(self, company_name: str, queries: list[str] | None = None, results_per_query: int = DEFAULT_RESULTS_PER_QUERY):
        self.company_name = company_name
        self.queries = queries if queries is not None else default_query_terms()
        self.results_per_query = results_per_query

    async def _search(self, client, query: str) -> list[RawJob]:  # pragma: no cover - overridden
        raise NotImplementedError

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def discover(self) -> list[RawJob]:
        seen: dict[str, RawJob] = {}
        async with build_http_client() as client:
            for query in self.queries:
                for job in await self._search(client, query):
                    seen.setdefault(job.source_job_id, job)
        jobs = list(seen.values())
        logger.info(f"{self.source_key}.discover", company=self.company_name, queries=len(self.queries), count=len(jobs))
        return jobs


class MicrosoftCareersSource(_QueryDrivenSource):
    """careers.microsoft.com search API (the endpoint its own SPA calls).

        GET https://gcsservices.careers.microsoft.com/search/api/v1/search
            ?q={query}&l=en_us&pg=1&pgSz=20&o=Relevance&flt=true
    """

    source_key = "microsoft"
    SEARCH_URL = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
    DETAIL_URL = "https://gcsservices.careers.microsoft.com/search/api/v1/job/{job_id}"

    def __init__(self, company_name: str = "Microsoft", **kwargs):
        super().__init__(company_name, **kwargs)
        self.name = "careersite:microsoft"

    async def _search(self, client, query: str) -> list[RawJob]:
        try:
            resp = await client.get(
                self.SEARCH_URL,
                params={"q": query, "l": "en_us", "pg": 1, "pgSz": self.results_per_query, "o": "Relevance", "flt": "true"},
                headers={"Accept": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"{self.name}: request failed: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

        result = (resp.json().get("operationResult") or {}).get("result")
        if not isinstance(result, dict) or "jobs" not in result:
            raise SourceError(f"{self.name}: unexpected payload shape (no operationResult.result.jobs) - API may have changed")

        jobs = []
        for job in result.get("jobs") or []:
            props = job.get("properties") or {}
            locations = props.get("locations") or []
            location = props.get("primaryLocation") or (locations[0] if locations else None)
            flexibility = props.get("workSiteFlexibility")
            jobs.append(RawJob(
                source="microsoft",
                source_job_id=str(job.get("jobId", "")),
                source_url=f"https://jobs.careers.microsoft.com/global/en/job/{job.get('jobId', '')}",
                company_name=self.company_name,
                job_title=job.get("title", ""),
                location_raw=", ".join(x for x in [location, flexibility] if x),
                updated_at=_parse_dt(job.get("postingDate")),
                collection_method=CollectionMethod.CAREER_SITE,
                raw_payload=job,
            ))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        async with build_http_client() as client:
            try:
                resp = await client.get(
                    self.DETAIL_URL.format(job_id=job.source_job_id),
                    params={"lang": "en_us"},
                    headers={"Accept": "application/json"},
                )
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: detail request failed: {exc}") from exc
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: detail request returned {resp.status_code}")
            payload = resp.json()

        result = (payload.get("operationResult") or {}).get("result") or {}
        props = result.get("properties") or {}
        parts = [
            props.get("description"),
            props.get("responsibilities"),
            props.get("qualifications"),
            f"Work site flexibility: {props['workSiteFlexibility']}" if props.get("workSiteFlexibility") else None,
        ]
        return RawJobDetails(
            raw_job=job,
            description_html="\n".join(p for p in parts if p) or None,
            published_at=_parse_dt(result.get("postingDate")) or job.updated_at,
            raw_payload=payload,
        )


class AmazonJobsSource(_QueryDrivenSource):
    """amazon.jobs public search JSON (used by its own careers site).

        GET https://www.amazon.jobs/en/search.json
            ?base_query={query}&result_limit=20&offset=0&sort=recent
    """

    source_key = "amazon"
    SEARCH_URL = "https://www.amazon.jobs/en/search.json"

    def __init__(self, company_name: str = "Amazon", **kwargs):
        super().__init__(company_name, **kwargs)
        self.name = "careersite:amazon"

    async def _search(self, client, query: str) -> list[RawJob]:
        try:
            resp = await client.get(
                self.SEARCH_URL,
                params={"base_query": query, "result_limit": self.results_per_query, "offset": 0, "sort": "recent"},
                headers={"Accept": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"{self.name}: request failed: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

        payload = resp.json()
        if "jobs" not in payload:
            raise SourceError(f"{self.name}: unexpected payload shape (no 'jobs' key) - API may have changed")

        jobs = []
        for job in payload.get("jobs") or []:
            path = job.get("job_path", "")
            jobs.append(RawJob(
                source="amazon",
                source_job_id=str(job.get("id_icims") or job.get("id", "")),
                source_url=f"https://www.amazon.jobs{path}" if path.startswith("/") else path,
                company_name=self.company_name,
                job_title=job.get("title", ""),
                location_raw=job.get("normalized_location") or job.get("location"),
                updated_at=_parse_dt(job.get("posted_date")),
                collection_method=CollectionMethod.CAREER_SITE,
                raw_payload=job,
            ))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        # search.json already returns the full description and both
        # qualification blocks - no second request needed.
        payload = job.raw_payload
        parts = [
            payload.get("description"),
            payload.get("basic_qualifications"),
            payload.get("preferred_qualifications"),
        ]
        return RawJobDetails(
            raw_job=job,
            description_html="\n".join(p for p in parts if p) or None,
            published_at=_parse_dt(payload.get("posted_date")) or job.updated_at,
            raw_payload=payload,
        )


class GoogleCareersSource(_QueryDrivenSource):
    """careers.google.com public search JSON.

        GET https://careers.google.com/api/v3/search/?q={query}&page=1
    """

    source_key = "google"
    SEARCH_URL = "https://careers.google.com/api/v3/search/"

    def __init__(self, company_name: str = "Google", **kwargs):
        super().__init__(company_name, **kwargs)
        self.name = "careersite:google"

    async def _search(self, client, query: str) -> list[RawJob]:
        try:
            resp = await client.get(
                self.SEARCH_URL,
                params={"q": query, "page": 1},
                headers={"Accept": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"{self.name}: request failed: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

        payload = resp.json()
        if "jobs" not in payload:
            raise SourceError(f"{self.name}: unexpected payload shape (no 'jobs' key) - API may have changed")

        jobs = []
        for job in payload.get("jobs") or []:
            job_id = str(job.get("id", "")).rsplit("/", 1)[-1]
            jobs.append(RawJob(
                source="google",
                source_job_id=job_id,
                source_url=job.get("apply_url") or f"https://www.google.com/about/careers/applications/jobs/results/{job_id}",
                company_name=self.company_name,
                job_title=job.get("title", ""),
                location_raw=_google_locations(job),
                updated_at=_parse_dt(job.get("publish_date")),
                collection_method=CollectionMethod.CAREER_SITE,
                raw_payload=job,
            ))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        parts = [payload.get("summary"), payload.get("description"), payload.get("qualifications"), payload.get("responsibilities")]
        return RawJobDetails(
            raw_job=job,
            description_html="\n".join(p for p in parts if isinstance(p, str) and p) or None,
            published_at=_parse_dt(payload.get("publish_date")) or job.updated_at,
            raw_payload=payload,
        )


def _google_locations(job: dict) -> str | None:
    locations = job.get("locations") or []
    names = []
    for loc in locations:
        if isinstance(loc, str):
            names.append(loc)
        elif isinstance(loc, dict):
            display = loc.get("display") or loc.get("city") or loc.get("country")
            if display:
                names.append(display)
    return "; ".join(names) or None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    for parser in (datetime.fromisoformat, lambda v: datetime.strptime(v, "%B %d, %Y")):
        try:
            return parser(text)
        except (ValueError, TypeError):
            continue
    return None
