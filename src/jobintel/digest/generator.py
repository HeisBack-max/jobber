"""Daily digest of new worthwhile opportunities (spec §43). Default max
20 opportunities - never overwhelm Richard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jobintel.db.models import Gig, Job, JobAnalysisRecord
from jobintel.db.session import session_scope
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
                f"{item.company_name} ({item.remote_classification})\n  {item.canonical_url}"
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

        rows = (
            session.query(Job, JobAnalysisRecord)
            .join(JobAnalysisRecord, JobAnalysisRecord.job_id == Job.id)
            .filter(Job.first_seen_at >= cutoff, JobAnalysisRecord.overall_score >= min_score)
            .order_by(JobAnalysisRecord.overall_score.desc())
            .limit(max_items)
            .all()
        )
        items = [
            DigestItem(
                job_title=job.job_title, company_name=job.company_name,
                overall_score=analysis.overall_score, recommendation=analysis.recommendation,
                remote_classification=job.remote_classification, canonical_url=job.canonical_url,
            )
            for job, analysis in rows
        ]

    return DigestResult(
        jobs_discovered=jobs_discovered,
        passed_hard_filters=passed_hard_filters,
        ai_evaluated=ai_evaluated,
        strong_matches=strong_matches,
        exceptional_matches=exceptional_matches,
        high_quality_gigs=high_quality_gigs,
        items=items,
    )
