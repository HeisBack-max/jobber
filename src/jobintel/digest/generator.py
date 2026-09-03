"""Daily digest of new worthwhile opportunities (spec §43). Default max
20 opportunities - never overwhelm Richard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jobintel.db.models import Gig, Job, JobAnalysisRecord
from jobintel.db.session import session_scope
from jobintel.models.enums import EligibilityStatus
from jobintel.settings import load_profile

_STRONG_RECOMMENDATIONS = {"STRONG_APPLY", "EXCEPTIONAL_MATCH"}


@dataclass
class DigestItem:
    job_title: str
    company_name: str
    overall_score: float
    recommendation: str
    remote_classification: str
    canonical_url: str
    locations: list[str] = field(default_factory=list)


@dataclass
class DigestResult:
    jobs_discovered: int
    passed_hard_filters: int
    ai_evaluated: int
    strong_matches: int
    exceptional_matches: int
    high_quality_gigs: int
    items: list[DigestItem] = field(default_factory=list)

    def render_text(self) -> str:
        lines = [
            "Daily Remote Job Brief",
            "",
            f"Jobs discovered: {self.jobs_discovered}",
            f"Passed hard filters: {self.passed_hard_filters}",
            f"AI evaluated: {self.ai_evaluated}",
            f"Strong matches: {self.strong_matches}",
            f"Exceptional matches: {self.exceptional_matches}",
            f"High-quality gigs: {self.high_quality_gigs}",
            "",
        ]
        for item in self.items:
            lines.append(
                f"{item.overall_score:.0f} - {item.recommendation} - {item.job_title} @ "
                f"{item.company_name} ({item.remote_classification})"
                + (f"\n  also open in: {'; '.join(item.locations[1:])}" if len(item.locations) > 1 else "")
                + f"\n  {item.canonical_url}"
            )
        return "\n".join(lines)


def generate_digest(since_hours: int = 24) -> DigestResult:
    profile = load_profile()
    max_items = profile.get("digest", {}).get("max_opportunities", 20)
    min_score = profile.get("scoring", {}).get("minimum_digest_score", 75)
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)

    with session_scope() as session:
        jobs_discovered = session.query(Job).filter(Job.first_seen_at >= cutoff).count()
        passed_hard_filters = (
            session.query(Job)
            .filter(Job.first_seen_at >= cutoff, Job.candidate_geographically_eligible != "NO")
            .count()
        )
        ai_evaluated = (
            session.query(JobAnalysisRecord)
            .join(Job, Job.id == JobAnalysisRecord.job_id)
            .filter(Job.first_seen_at >= cutoff)
            .count()
        )
        strong_matches = (
            session.query(JobAnalysisRecord)
            .join(Job, Job.id == JobAnalysisRecord.job_id)
            .filter(Job.first_seen_at >= cutoff, JobAnalysisRecord.recommendation == "STRONG_APPLY")
            .count()
        )
        exceptional_matches = (
            session.query(JobAnalysisRecord)
            .join(Job, Job.id == JobAnalysisRecord.job_id)
            .filter(Job.first_seen_at >= cutoff, JobAnalysisRecord.recommendation == "EXCEPTIONAL_MATCH")
            .count()
        )
        high_quality_gigs = (
            session.query(Gig)
            .join(Job, Job.id == Gig.job_id)
            .filter(Job.first_seen_at >= cutoff, Gig.gig_quality_score >= min_score)
            .count()
        )

        # The brief is "signal over volume": never spend a slot on a role the
        # candidate is not geographically eligible for, and never spend several
        # slots on one role that a company has posted per-location. Collapsing
        # happens after the fetch, so the cap applies to distinct roles.
        rows = (
            session.query(Job, JobAnalysisRecord)
            .join(JobAnalysisRecord, JobAnalysisRecord.job_id == Job.id)
            .filter(
                Job.first_seen_at >= cutoff,
                JobAnalysisRecord.overall_score >= min_score,
                Job.candidate_geographically_eligible != EligibilityStatus.NO.value,
            )
            .order_by(JobAnalysisRecord.overall_score.desc())
            .limit(max_items * 10)
            .all()
        )
        by_role: dict[tuple[str, str], DigestItem] = {}
        for job, analysis in rows:
            key = (job.job_title.strip().casefold(), job.company_name.strip().casefold())
            existing = by_role.get(key)
            if existing is None:
                by_role[key] = DigestItem(
                    job_title=job.job_title, company_name=job.company_name,
                    overall_score=analysis.overall_score, recommendation=analysis.recommendation,
                    remote_classification=job.remote_classification,
                    canonical_url=job.canonical_url,
                    locations=[job.location_raw] if job.location_raw else [],
                )
            elif job.location_raw and job.location_raw not in existing.locations:
                existing.locations.append(job.location_raw)
        items = list(by_role.values())[:max_items]

    return DigestResult(
        jobs_discovered=jobs_discovered,
        passed_hard_filters=passed_hard_filters,
        ai_evaluated=ai_evaluated,
        strong_matches=strong_matches,
        exceptional_matches=exceptional_matches,
        high_quality_gigs=high_quality_gigs,
        items=items,
    )
