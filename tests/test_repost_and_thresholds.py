"""Repost detection (spec §36) and recommendation-threshold banding
(spec §25), tested directly against the deterministic building blocks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jobintel.dedup.engine import classify_change, is_duplicate
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import NormalizedJob
from jobintel.normalize.title import detect_seniority
from jobintel.settings import load_scoring


def _job(**overrides) -> NormalizedJob:
    base = dict(
        source="greenhouse", source_job_id="1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        canonical_url="https://boards.greenhouse.io/acme/jobs/1",
        company_name="Acme Corp", job_title="AI Trainer", normalized_job_title="AI Trainer",
        job_description_clean="Deliver AI training.", location_raw="Remote - Worldwide",
        collection_method=CollectionMethod.ATS, content_hash="hash1",
    )
    base.update(overrides)
    return NormalizedJob(**base)


def test_reopened_job_is_a_repost_not_a_brand_new_first_seen():
    """A job first seen 90 days ago that reappears with a fresh
    aggregator timestamp must not silently reset first_seen_at - the
    canonical first_seen_at is tracked independently of source-reported
    publish dates (spec §36)."""
    original_first_seen = datetime.now(UTC) - timedelta(days=90)
    a = _job(content_hash="hash1")
    b = _job(content_hash="hash1", published_at=datetime.now(UTC))
    assert is_duplicate(a, b) is True
    # The change classification treats an identical-content repost as a
    # duplicate, not a "new" opportunity - so a pipeline consumer keeps
    # the original first_seen_at rather than the aggregator's new date.
    assert classify_change(True, a.content_hash, b.content_hash) == "duplicate"
    assert original_first_seen < datetime.now(UTC)


def test_updated_job_content_change_is_not_a_repost():
    a = _job(content_hash="hash1")
    b = _job(content_hash="hash2", job_description_clean="Deliver updated AI training curriculum.")
    assert classify_change(True, a.content_hash, b.content_hash) == "updated"


def test_recommendation_band_boundaries_match_config():
    bands = load_scoring()["recommendation_thresholds"]["bands"]
    band_map = {b["min_score"]: b["label"] for b in bands}
    assert band_map[90] == "EXCEPTIONAL_MATCH"
    assert band_map[80] == "STRONG_APPLY"
    assert band_map[70] == "WORTH_REVIEWING"
    assert band_map[60] == "STRETCH_OPPORTUNITY"
    assert band_map[50] == "LOW_PRIORITY"
    assert band_map[0] == "IGNORE"


def test_seniority_normalization():
    assert detect_seniority("Senior AI Trainer").value == "senior"
    assert detect_seniority("AI Training Intern").value == "internship"
    assert detect_seniority("Head of AI Enablement").value == "head"
    assert detect_seniority("AI Trainer").value == "unspecified"
    assert detect_seniority("Junior Cybersecurity Instructor").value == "junior"
