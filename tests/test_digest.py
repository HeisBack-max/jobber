"""Daily brief selection tests.

The brief is the product's headline output and its stated contract is
"signal over volume" (README): a small number of genuinely worthwhile,
remote-compatible opportunities. These tests pin the two selection rules
that contract implies.
"""

from __future__ import annotations

from datetime import UTC, datetime

from jobintel.models.enums import EligibilityStatus


def _job(session, Job, *, jid, title, company, location, eligible=EligibilityStatus.YES.value,
         remote_classification="REMOTE_EMEA"):
    job = Job(
        source="fake", source_job_id=jid, source_url=f"https://x/{jid}",
        canonical_url=f"https://x/{jid}", company_name=company, job_title=title,
        normalized_job_title=title.lower(), content_hash=jid,
        location_raw=location, remote_classification=remote_classification,
        candidate_geographically_eligible=eligible,
        first_seen_at=datetime.now(UTC),
    )
    session.add(job)
    session.flush()
    return job


def _analysis(session, Rec, job, score, recommendation):
    session.add(Rec(
        job_id=job.id, remote_score=score, experience_score=score, skills_score=score,
        training_advantage_score=score, ai_cyber_intersection_score=score,
        interview_probability_score=score, compensation_score=score, freshness_score=score,
        can_do_score=score, desirability_score=score, overall_score=score,
        confidence_score=0.9, recommendation=recommendation,
    ))


def test_ineligible_roles_never_take_a_brief_slot(temp_db):
    """A geographically ineligible role must not appear, however high it scores."""
    from jobintel.db.models import Job, JobAnalysisRecord
    from jobintel.digest.generator import generate_digest

    with temp_db.session_scope() as s:
        ok = _job(s, Job, jid="1", title="AI Trainer", company="Acme", location="Remote - EMEA")
        _analysis(s, JobAnalysisRecord, ok, 88, "STRONG_APPLY")
        bad = _job(s, Job, jid="2", title="US Only Role", company="Acme",
                   location="San Francisco, CA", eligible=EligibilityStatus.NO.value,
                   remote_classification="REMOTE_US_ONLY")
        _analysis(s, JobAnalysisRecord, bad, 95, "INELIGIBLE")

    titles = [i.job_title for i in generate_digest().items]
    assert "AI Trainer" in titles
    assert "US Only Role" not in titles


def test_one_role_posted_per_location_collapses_to_one_slot(temp_db):
    """A role a company lists in several cities is one opportunity, not many."""
    from jobintel.db.models import Job, JobAnalysisRecord
    from jobintel.digest.generator import generate_digest

    with temp_db.session_scope() as s:
        for n, loc in enumerate(("Amsterdam, Netherlands", "Paris, France", "Munich, Germany"), start=1):
            j = _job(s, Job, jid=str(n), title="Solutions Architect", company="Acme", location=loc)
            _analysis(s, JobAnalysisRecord, j, 90 - n, "STRONG_APPLY")

    items = generate_digest().items
    assert len(items) == 1, "the same role in 3 cities must occupy one slot"
    assert items[0].overall_score == 89, "the highest-scoring posting wins"
    assert len(items[0].locations) == 3
    assert "Paris, France" in "; ".join(items[0].locations)


def test_distinct_roles_are_not_collapsed(temp_db):
    """Collapsing must key on role+company, never merge genuinely different roles."""
    from jobintel.db.models import Job, JobAnalysisRecord
    from jobintel.digest.generator import generate_digest

    with temp_db.session_scope() as s:
        a = _job(s, Job, jid="1", title="AI Trainer", company="Acme", location="Remote - EMEA")
        _analysis(s, JobAnalysisRecord, a, 88, "STRONG_APPLY")
        b = _job(s, Job, jid="2", title="AI Trainer", company="Globex", location="Remote - EMEA")
        _analysis(s, JobAnalysisRecord, b, 87, "STRONG_APPLY")
        c = _job(s, Job, jid="3", title="Security Architect", company="Acme", location="Remote - EMEA")
        _analysis(s, JobAnalysisRecord, c, 86, "STRONG_APPLY")

    assert len(generate_digest().items) == 3
