"""Search-discovery collectors (spec §31, Milestone 6).

The ATS collectors only find vacancies at employers Richard already
knows to watch. Search discovery is the other half: it runs the query
families in config/search_queries.yaml against public remote-job search
APIs, so a role that matches his profile surfaces even when it is posted
by a company nobody put on the watchlist - and so a strategic employer
with no collectable ATS (Meta, Hugging Face) still has *a* channel.

Provenance matters here. Aggregator listings are second-hand: they can
be stale, truncated, reposted, or missing the employer's own
geography/travel language, which is precisely the text the eligibility
engine depends on. So every job discovered this way is recorded with
`source_type="aggregator"` and a worse `quality_rank` than an ATS
record, which means:

  * if the same vacancy is later collected from the employer's own ATS,
    the ATS text wins and overwrites the aggregator copy (dedup engine
    `should_overwrite`), and
  * a job known *only* through an aggregator takes the
    `aggregator_only_source` confidence deduction from
    config/scoring.yaml rather than being presented as equally certain.

Both backends here are public, unauthenticated, documented JSON APIs
intended for programmatic use. Nothing logs in, and nothing scrapes HTML.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from jobintel.collectors.base import JobSource, SourceError, build_http_client
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails
from jobintel.settings import load_search_queries

logger = structlog.get_logger()

DEFAULT_LIMIT_PER_QUERY = 25


def query_terms(families: list[str] | None = None, limit: int | None = None) -> list[str]:
    """Bare keyword terms from config/search_queries.yaml.

    The stored queries are search-engine syntax ('"AI trainer" remote');
    job-search APIs want a plain keyword string, so quotes and the
    "remote"/"jobs" noise words come off.
    """
    data = load_search_queries().get("query_families", {})
    selected = {k: v for k, v in data.items() if families is None or k in families}
    terms: list[str] = []
    for family in selected.values():
        for query in family.get("queries", []):
            cleaned = " ".join(
                word for word in query.replace('"', " ").split()
                if word.lower() not in {"remote", "jobs", "job"}
            ).strip()
            if cleaned and cleaned not in terms:
                terms.append(cleaned)
    return terms[:limit] if limit else terms


class _SearchDiscoverySource(JobSource):
    """Common behaviour for aggregator-backed discovery."""

    # Second-hand listings: never allowed to overwrite employer-sourced text.
    source_type = "aggregator"
    quality_rank = 4

    def __init__(self, families: list[str] | None = None, max_queries: int = 8, limit_per_query: int = DEFAULT_LIMIT_PER_QUERY):
        self.queries = query_terms(families, limit=max_queries)
        self.limit_per_query = limit_per_query

    async def _run_query(self, client, query: str) -> list[RawJob]:  # pragma: no cover - overridden
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
                for job in await self._run_query(client, query):
                    seen.setdefault(job.source_job_id, job)
        jobs = list(seen.values())
        logger.info("search_discovery.discover", source=self.name, queries=len(self.queries), count=len(jobs))
        return jobs


class RemotiveSearchSource(_SearchDiscoverySource):
    """Remotive public API: https://remotive.com/api/remote-jobs?search=..."""

    name = "search:remotive"
    SEARCH_URL = "https://remotive.com/api/remote-jobs"

    async def _run_query(self, client, query: str) -> list[RawJob]:
        try:
            resp = await client.get(self.SEARCH_URL, params={"search": query, "limit": self.limit_per_query})
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"{self.name}: request failed: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"{self.name}: unexpected status {resp.status_code}")

        payload = resp.json()
        if "jobs" not in payload:
            raise SourceError(f"{self.name}: unexpected payload shape (no 'jobs' key) - API may have changed")

        jobs = []
        for job in payload.get("jobs") or []:
            jobs.append(RawJob(
                source="remotive",
                source_job_id=str(job.get("id", "")),
                source_url=job.get("url", ""),
                company_name=job.get("company_name", "").strip(),
                job_title=job.get("title", ""),
                # Remotive's own field for "who may hold this job", which
                # is exactly the geography question that matters here.
                location_raw=job.get("candidate_required_location"),
                updated_at=_parse_dt(job.get("publication_date")),
                collection_method=CollectionMethod.SEARCH_DISCOVERY,
                raw_payload=job,
            ))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        return RawJobDetails(
            raw_job=job,
            description_html=payload.get("description"),
            salary_raw=payload.get("salary") or None,
            published_at=_parse_dt(payload.get("publication_date")) or job.updated_at,
            raw_payload=payload,
        )


class RemoteOKSearchSource(_SearchDiscoverySource):
    """RemoteOK public API: https://remoteok.com/api

    Returns the whole current board in one response (no server-side
    search), so filtering happens client-side against the same query
    terms. The first element of the response is RemoteOK's legal/
    attribution notice, not a job - it is skipped, and the notice text is
    logged so the attribution requirement stays visible rather than
    being quietly dropped.
    """

    name = "search:remoteok"
    SEARCH_URL = "https://remoteok.com/api"

    async def discover(self) -> list[RawJob]:
        async with build_http_client() as client:
            try:
                resp = await client.get(self.SEARCH_URL)
            except Exception as exc:  # noqa: BLE001
                raise SourceError(f"{self.name}: request failed: {exc}") from exc
            if resp.status_code != 200:
                raise SourceError(f"{self.name}: unexpected status {resp.status_code}")
            payload = resp.json()

        if not isinstance(payload, list):
            raise SourceError(f"{self.name}: unexpected payload shape (expected a list) - API may have changed")

        patterns = [re.compile(re.escape(term), re.I) for term in self.queries]
        jobs: list[RawJob] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            if "legal" in entry:
                logger.info("search_discovery.remoteok_attribution", notice=entry["legal"])
                continue
            haystack = " ".join(str(entry.get(k, "")) for k in ("position", "description", "tags"))
            if patterns and not any(p.search(haystack) for p in patterns):
                continue
            jobs.append(RawJob(
                source="remoteok",
                source_job_id=str(entry.get("id") or entry.get("slug", "")),
                source_url=entry.get("url") or entry.get("apply_url", ""),
                company_name=(entry.get("company") or "").strip(),
                job_title=entry.get("position", ""),
                location_raw=entry.get("location"),
                updated_at=_parse_dt(entry.get("date")) or _epoch_to_dt(entry.get("epoch")),
                collection_method=CollectionMethod.SEARCH_DISCOVERY,
                raw_payload=entry,
            ))

        logger.info("search_discovery.discover", source=self.name, queries=len(self.queries), count=len(jobs))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        payload = job.raw_payload
        salary_min, salary_max = payload.get("salary_min"), payload.get("salary_max")
        salary_raw = f"USD {salary_min}-{salary_max} year" if salary_min or salary_max else None
        return RawJobDetails(
            raw_job=job,
            description_html=payload.get("description"),
            salary_raw=salary_raw,
            published_at=job.updated_at,
            raw_payload=payload,
        )


SEARCH_BACKENDS = {
    "remotive": RemotiveSearchSource,
    "remoteok": RemoteOKSearchSource,
}


def build_search_sources(enabled: list[str] | None = None, families: list[str] | None = None) -> list[JobSource]:
    """Instantiate the configured search-discovery backends.

    Driven by the `search_discovery` block in config/search_queries.yaml
    so enabling a backend is a config change, not a code change.
    """
    config = load_search_queries().get("search_discovery", {}) or {}
    if enabled is None:
        enabled = [name for name, on in (config.get("backends") or {}).items() if on]
    families = families if families is not None else config.get("families")
    # `max_queries_per_run` is the knob that bounds outbound request
    # volume, so it has to actually reach the source - it was previously
    # read from config by nothing and silently left at the default.
    max_queries = int(config.get("max_queries_per_run", 8))
    return [
        SEARCH_BACKENDS[name](families=families, max_queries=max_queries)
        for name in enabled
        if name in SEARCH_BACKENDS
    ]


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _epoch_to_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (ValueError, OSError, OverflowError, TypeError):
        return None
