"""Decides *what* gets sent and *when*, over whatever channels are
configured (spec §43/§44).

Two kinds of outbound message, deliberately different in urgency:

* the daily digest - the normal channel, one message a day, and
* urgent alerts - reserved for an exceptional, eligible, confirmed-remote
  role posted in the last day (thresholds in config/profile.yaml).

Every send is recorded in `notification_log`, which is what makes
"alert once per job" true across runs. A notifier that re-sends the same
job every morning teaches its reader to ignore it, which is worse than
not alerting at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from jobintel.db.models import Job, JobAnalysisRecord, NotificationLog
from jobintel.db.session import session_scope
from jobintel.notifications.base import NotificationAdapter, get_enabled_adapters, urgent_alert_condition
from jobintel.settings import load_profile

logger = structlog.get_logger()

URGENT_ALERT = "urgent_alert"
DAILY_DIGEST = "daily_digest"
TEST_MESSAGE = "test"


@dataclass
class DispatchSummary:
    channels: list[str] = field(default_factory=list)
    urgent_alerts_sent: int = 0
    digests_sent: int = 0
    failures: list[str] = field(default_factory=list)
    skipped_already_alerted: int = 0

    def render(self) -> str:
        if not self.channels:
            return "Notifications: no channels configured (nothing sent)."
        return (
            f"Notifications: channels={', '.join(self.channels)}; "
            f"urgent alerts sent={self.urgent_alerts_sent}; "
            f"digests sent={self.digests_sent}; "
            f"already-alerted jobs skipped={self.skipped_already_alerted}; "
            f"failures={len(self.failures)}"
            + ("".join(f"\n  - {f}" for f in self.failures) if self.failures else "")
        )


def _naive_utcnow() -> datetime:
    """SQLite returns naive datetimes; comparisons must match that shape."""
    return datetime.now(UTC).replace(tzinfo=None)


def _age_hours(job: Job) -> float:
    reference = job.published_at or job.first_seen_at
    if reference is None:
        return float("inf")
    if reference.tzinfo is not None:
        reference = reference.astimezone(UTC).replace(tzinfo=None)
    return max(0.0, (_naive_utcnow() - reference).total_seconds() / 3600)


def find_urgent_opportunities(session, limit: int = 10) -> list[tuple[Job, JobAnalysisRecord]]:
    """Jobs meeting the urgent-alert bar that have not been alerted on."""
    profile = load_profile().get("alerts", {}) or {}
    suppress_duplicates = bool(profile.get("suppress_duplicate_alerts", True))

    rows = (
        session.query(Job, JobAnalysisRecord)
        .join(JobAnalysisRecord, JobAnalysisRecord.job_id == Job.id)
        .filter(Job.is_active.is_(True))
        .order_by(JobAnalysisRecord.overall_score.desc())
        .limit(200)
        .all()
    )

    already_alerted: set[str] = set()
    if suppress_duplicates:
        already_alerted = {
            row.job_id
            for row in session.query(NotificationLog)
            .filter(NotificationLog.kind == URGENT_ALERT, NotificationLog.status == "SENT")
            .all()
            if row.job_id
        }

    urgent = []
    for job, analysis in rows:
        if job.id in already_alerted:
            continue
        if not urgent_alert_condition(
            overall_score=analysis.overall_score,
            age_hours=_age_hours(job),
            geographically_eligible=job.candidate_geographically_eligible == "YES",
            remote_confirmed=job.remote_classification.startswith("REMOTE_"),
        ):
            continue
        urgent.append((job, analysis))
        if len(urgent) >= limit:
            break
    return urgent


def format_urgent_alert(job: Job, analysis: JobAnalysisRecord) -> tuple[str, str]:
    subject = f"Urgent match ({analysis.overall_score:.0f}): {job.job_title} @ {job.company_name}"
    lines = [
        f"{job.job_title} - {job.company_name}",
        f"Score {analysis.overall_score:.0f}/100 ({analysis.recommendation}), "
        f"confidence {analysis.confidence_score:.0f}%",
        f"Remote: {job.remote_classification} | Eligibility: {job.candidate_geographically_eligible}",
        "",
        analysis.reasoning_summary or "",
    ]
    if analysis.strengths:
        lines += ["", "Why you fit:"] + [f"- {s}" for s in analysis.strengths[:4]]
    if analysis.mandatory_mismatches:
        lines += ["", "Mandatory mismatches:"] + [f"- {m}" for m in analysis.mandatory_mismatches]
    lines += ["", job.canonical_url or job.source_url]
    return subject, "\n".join(lines)


async def dispatch_notifications(
    adapters: list[NotificationAdapter] | None = None,
    include_digest: bool = True,
    include_urgent: bool = True,
) -> DispatchSummary:
    adapters = get_enabled_adapters() if adapters is None else adapters
    summary = DispatchSummary(channels=[a.name for a in adapters])
    if not adapters:
        # Not an error: notifications are optional by design (spec §44).
        logger.info("notifications.no_channels_configured")
        return summary

    profile_alerts = load_profile().get("alerts", {}) or {}

    with session_scope() as session:
        if include_urgent:
            for job, analysis in find_urgent_opportunities(session):
                subject, body = format_urgent_alert(job, analysis)
                sent_any = False
                for adapter in adapters:
                    result = await adapter.send(subject, body)
                    session.add(NotificationLog(
                        job_id=job.id, channel=adapter.name, kind=URGENT_ALERT,
                        status="SENT" if result.ok else "FAILED", error=result.error,
                    ))
                    if result.ok:
                        sent_any = True
                    else:
                        summary.failures.append(f"{adapter.name}: {result.error}")
                if sent_any:
                    summary.urgent_alerts_sent += 1

        if include_digest and profile_alerts.get("send_daily_digest", True):
            from jobintel.digest.generator import generate_digest

            digest = generate_digest()
            if digest.items or digest.jobs_discovered:
                subject = f"Daily Remote Job Brief - {len(digest.items)} opportunities"
                body = digest.render_text()
                for adapter in adapters:
                    result = await adapter.send(subject, body)
                    session.add(NotificationLog(
                        channel=adapter.name, kind=DAILY_DIGEST,
                        status="SENT" if result.ok else "FAILED", error=result.error,
                    ))
                    if result.ok:
                        summary.digests_sent += 1
                    else:
                        summary.failures.append(f"{adapter.name}: {result.error}")

    return summary


async def send_test_message(adapters: list[NotificationAdapter] | None = None) -> DispatchSummary:
    """`jobintel notify --test`: prove a channel actually works before
    relying on it, rather than discovering it was misconfigured on the
    day something exceptional turns up."""
    adapters = get_enabled_adapters() if adapters is None else adapters
    summary = DispatchSummary(channels=[a.name for a in adapters])
    for adapter in adapters:
        result = await adapter.send(
            "Remote Job Intelligence - test message",
            "If you can read this, this notification channel is configured correctly.",
        )
        if not result.ok:
            summary.failures.append(f"{adapter.name}: {result.error}")
        else:
            summary.digests_sent += 1
    return summary
