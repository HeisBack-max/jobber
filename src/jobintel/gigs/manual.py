"""Manual gig entry (config/manual_gigs.yaml).

The honest answer to platforms that cannot be collected: Outlier AI and
comparable expert marketplaces only show project listings behind a
login, and scraping an authenticated session is out of scope for good
reasons (see outlier.py). What Richard *can* do is paste a project he
found there into config/manual_gigs.yaml, and have it scored, ranked,
tracked and digested exactly like everything the collectors found on
their own.

This is deliberately a `JobSource`, not a `GigSource`: routing manual
entries through the ordinary collection path means they get normalized,
deduplicated, geography-classified, persisted and gig-scored by the same
code as every other posting, rather than through a private path that
would drift out of sync. The `GigSource` interface stays for a future
platform that publishes a real API.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
import yaml

from jobintel.collectors.base import JobSource
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob, RawJobDetails
from jobintel.settings import CONFIG_DIR

logger = structlog.get_logger()

MANUAL_GIGS_FILE = "manual_gigs.yaml"


class ManualGigSource(JobSource):
    name = "manual:gigs"
    # First-hand: Richard copied this from the platform himself, so it
    # outranks an aggregator but not the employer's own ATS text.
    source_type = "manual_entry"
    quality_rank = 2

    def __init__(self, path=None):
        self._path = path or (CONFIG_DIR / MANUAL_GIGS_FILE)

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return [entry for entry in (data.get("gigs") or []) if entry.get("title")]

    def has_entries(self) -> bool:
        """Lets the registry skip building this source at all when the
        file is empty, so an empty manual list is not reported as a
        source that collected zero jobs."""
        return bool(self._load())

    async def discover(self) -> list[RawJob]:
        entries = self._load()
        jobs = []
        for index, entry in enumerate(entries):
            identifier = str(entry.get("id") or f"{entry.get('platform', 'manual')}-{index}")
            jobs.append(RawJob(
                source="manual",
                source_job_id=identifier,
                source_url=entry.get("url", ""),
                company_name=entry.get("platform") or entry.get("company") or "Manual entry",
                job_title=entry["title"],
                location_raw=entry.get("location"),
                updated_at=_parse_date(entry.get("posted_on")),
                collection_method=CollectionMethod.MANUAL_IMPORT,
                raw_payload=entry,
            ))
        logger.info("manual_gigs.discover", count=len(jobs))
        return jobs

    async def fetch_details(self, job: RawJob) -> RawJobDetails:
        entry = job.raw_payload
        description = entry.get("description", "")
        # Structured fields are appended to the description text so the
        # gig classifier and the geography engine - both of which read
        # text - see them without needing a second code path.
        extras = []
        if entry.get("hourly_rate"):
            extras.append(f"Rate: {entry['hourly_rate']} per hour.")
        if entry.get("weekly_hours"):
            extras.append(f"Expected commitment: {entry['weekly_hours']} hours per week.")
        if entry.get("duration"):
            extras.append(f"Project duration: {entry['duration']}.")
        if entry.get("employment_type"):
            extras.append(f"Engagement type: {entry['employment_type']}.")
        else:
            extras.append("Engagement type: independent contractor / project-based work.")

        return RawJobDetails(
            raw_job=job,
            description_text="\n".join([description, *extras]).strip(),
            salary_raw=entry.get("hourly_rate"),
            published_at=_parse_date(entry.get("posted_on")) or job.updated_at,
            raw_payload=entry,
        )


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
