"""Gig identification, scoring and persistence (spec §19/§20/§21).

The gig channel was the one deferred feature that could not be closed by
collecting Outlier AI - so what is tested here is the route that
actually works: contractor/project postings arriving through the ATS
boards this app already collects, plus manual entry for platforms that
publish nothing.
"""

from __future__ import annotations

import asyncio

import pytest
import yaml

from jobintel.gigs.classifier import classify_gig, extract_hourly_rate, extract_weekly_hours
from jobintel.gigs.manual import ManualGigSource

APPEN_STYLE_CONTRACTOR_POSTING = (
    "Join our team as an Independent Contractor for Project Morava. This is project-based "
    "work: you set your own hours, working 10-20 hours per week for a 6 weeks project. "
    "Rate: $25-35 per hour. Remote - Worldwide."
)
SPECIALIST_EVALUATION_GIG = (
    "LLM Security Evaluation Specialist - freelance, international remote, work from anywhere. "
    "$65-90 per hour, 10-20 hours per week. Adversarial testing, red team exercises and "
    "prompt-injection evaluation of enterprise LLM deployments."
)
PERMANENT_ROLE_MENTIONING_CONTRACTS = (
    "Senior Contract Manager - full-time permanent position. You will own contract management "
    "and contract negotiation across the vendor portfolio. Salary range $90,000 - $120,000 per year."
)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def test_contractor_project_posting_is_recognised_as_a_gig():
    signals = classify_gig("Voice Recording Specialist", APPEN_STYLE_CONTRACTOR_POSTING)
    assert signals.is_gig
    assert signals.hourly_rate_min == 25
    assert signals.hourly_rate_max == 35
    assert signals.rate_currency == "USD"
    assert (signals.weekly_hours_min, signals.weekly_hours_max) == (10, 20)
    assert signals.project_duration == "6 weeks"


def test_permanent_role_mentioning_contracts_is_not_a_gig():
    """The conservative half: routing a salaried role through gig scoring
    would judge it on an hourly rate it does not have."""
    signals = classify_gig("Senior Contract Manager", PERMANENT_ROLE_MENTIONING_CONTRACTS)
    assert signals.is_gig is False


def test_single_weak_signal_is_not_enough():
    signals = classify_gig(
        "Training Manager",
        "You will manage the contract training calendar for our enterprise customers.",
    )
    assert signals.is_gig is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$65-90 per hour", (65.0, 90.0, "USD")),
        ("£45 per hour", (45.0, 45.0, "GBP")),
        ("€30 - €40 /hr", (30.0, 40.0, "EUR")),
        ("competitive compensation", (None, None, None)),
    ],
)
def test_hourly_rate_extraction(text, expected):
    assert extract_hourly_rate(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10-20 hours per week", (10.0, 20.0)),
        ("up to 15 hours a week", (None, 15.0)),
        ("full commitment expected", (None, None)),
    ],
)
def test_weekly_hours_extraction(text, expected):
    assert extract_weekly_hours(text) == expected


# --------------------------------------------------------------------------
# Manual entry
# --------------------------------------------------------------------------

def test_manual_gig_file_ships_empty_and_collects_nothing(tmp_path):
    """An empty manual list must not register as a source at all - a
    source reporting "0 jobs" every run is noise in source health."""
    assert ManualGigSource().has_entries() is False

    from jobintel.discovery.registry import build_sources

    assert not any(s.name == "manual:gigs" for s in build_sources(include_search_discovery=False))


def test_manual_gig_entry_flows_through_the_normal_pipeline(tmp_path):
    path = tmp_path / "manual_gigs.yaml"
    path.write_text(yaml.safe_dump({
        "gigs": [{
            "id": "outlier-eval-1",
            "platform": "Outlier AI",
            "title": "LLM Safety Evaluation Specialist",
            "location": "Remote - Worldwide",
            "hourly_rate": "$50-70 per hour",
            "weekly_hours": "10-20",
            "duration": "8 weeks",
            "employment_type": "independent contractor",
            "posted_on": "2026-08-20",
            "description": "Evaluate model responses for safety, run adversarial prompts.",
        }]
    }), encoding="utf-8")

    source = ManualGigSource(path=path)
    assert source.has_entries()
    assert source.source_type == "manual_entry"

    jobs = asyncio.run(source.discover())
    assert len(jobs) == 1
    assert jobs[0].source_job_id == "outlier-eval-1"
    assert jobs[0].company_name == "Outlier AI"

    details = asyncio.run(source.fetch_details(jobs[0]))
    # The structured fields must reach the description text, since the
    # gig classifier and geography engine both read text.
    assert "50-70" in details.description_text
    assert "10-20 hours per week" in details.description_text
    assert "8 weeks" in details.description_text

    signals = classify_gig(jobs[0].job_title, details.description_text)
    assert signals.is_gig
    assert signals.hourly_rate_max == 70


def test_manual_entry_never_overwrites_an_employers_own_posting():
    from jobintel.dedup.engine import should_overwrite

    assert should_overwrite("official_ats", "manual_entry") is False
    assert should_overwrite("aggregator", "manual_entry") is True


# --------------------------------------------------------------------------
# End-to-end: collection -> gig identification -> scoring -> persistence
# --------------------------------------------------------------------------

def _seed_and_evaluate(temp_db, title, description, company="Appen"):
    from datetime import UTC, datetime

    from jobintel.db.models import Job
    from jobintel.pipeline import run_evaluation

    with temp_db.session_scope() as session:
        job = Job(
            source="lever", source_job_id="1", source_url="u", canonical_url="u",
            company_name=company, job_title=title, normalized_job_title=title.lower(),
            job_description_clean=description, location_raw="Remote - Worldwide",
            remote_classification="REMOTE_WORLDWIDE", candidate_geographically_eligible="YES",
            published_at=datetime.now(UTC).replace(tzinfo=None), content_hash="hash-1",
        )
        session.add(job)
    return run_evaluation()


def test_specialist_gig_is_identified_scored_and_stored(temp_db):
    from jobintel.db.models import Gig, GigAnalysisRecord, Job

    summary = _seed_and_evaluate(temp_db, "LLM Security Evaluation Specialist", SPECIALIST_EVALUATION_GIG)
    assert summary.gigs_identified == 1

    with temp_db.session_scope() as session:
        gig = session.query(Gig).one()
        assert gig.advertised_hourly_rate_max == 90
        assert gig.expected_weekly_hours_max == 20
        assert gig.gig_quality_score >= 60
        assert gig.specialist_classification == "specialist"

        analysis = session.query(GigAnalysisRecord).one()
        # Component breakdown, not a single opaque number (spec §65).
        assert analysis.compensation > 0
        assert analysis.geographic_compatibility > 0
        assert "Classified as gig work" in analysis.reasoning_summary

        job = session.query(Job).one()
        assert job.opportunity_class == "GIG_PROJECT_WORK"


def test_commodity_annotation_gig_is_capped_and_labelled(temp_db):
    from jobintel.db.models import Gig

    posting = (
        "Data Annotation Contributor - freelance, remote worldwide. Label images and text for "
        "machine learning datasets. $3-5 per hour, 10-20 hours per week. No specialist background required."
    )
    summary = _seed_and_evaluate(temp_db, "Data Annotation Contributor", posting, company="Toloka")
    assert summary.gigs_identified == 1

    with temp_db.session_scope() as session:
        gig = session.query(Gig).one()
        assert gig.gig_quality_score <= 35
        assert gig.specialist_classification == "commodity_annotation"


def test_gig_evaluation_is_idempotent(temp_db):
    from jobintel.db.models import Gig
    from jobintel.pipeline import run_evaluation

    _seed_and_evaluate(temp_db, "LLM Security Evaluation Specialist", SPECIALIST_EVALUATION_GIG)
    second = run_evaluation()

    assert second.gigs_identified == 0
    with temp_db.session_scope() as session:
        assert session.query(Gig).count() == 1


def test_permanent_role_does_not_become_a_gig(temp_db):
    from jobintel.db.models import Gig

    summary = _seed_and_evaluate(temp_db, "Senior Contract Manager", PERMANENT_ROLE_MENTIONING_CONTRACTS)
    assert summary.gigs_identified == 0
    with temp_db.session_scope() as session:
        assert session.query(Gig).count() == 0


def test_outlier_remains_explicitly_unimplemented():
    """The one thing that genuinely cannot be built stays honest rather
    than being faked with a stub that returns nothing."""
    from jobintel.gigs.outlier import OutlierGigSourceNotImplemented

    source = OutlierGigSourceNotImplemented()
    with pytest.raises(NotImplementedError):
        asyncio.run(source.discover())


def test_language_specific_project_is_a_mandatory_mismatch():
    """Real postings from the AI-data marketplaces are frequently
    language-specific ("[Croatian] - Voice Recording Specialist"), and
    the CV evidences English only - so these are a hard mismatch, not a
    soft gap, even though everything else about them fits the gig
    profile. The language marker is usually in the title alone."""
    from jobintel.matching.negative_matcher import find_mismatches

    result = find_mismatches(
        "Join our team as an Independent Contractor for Project Morava. Record voice samples.",
        job_title="[Croatian] - Voice Recording Specialist",
    )
    assert any("English only" in m for m in result.mandatory_mismatches)

    english_role = find_mismatches(
        "Deliver AI security training in English to enterprise customers across EMEA.",
        job_title="AI Security Trainer",
    )
    assert not any("English only" in m for m in english_role.mandatory_mismatches)
