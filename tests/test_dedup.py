from __future__ import annotations

from jobintel.dedup.engine import classify_change, is_duplicate, should_overwrite
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import NormalizedJob


def _job(**overrides) -> NormalizedJob:
    base = dict(
        source="greenhouse",
        source_job_id="123",
        source_url="https://boards.greenhouse.io/acme/jobs/123",
        canonical_url="https://boards.greenhouse.io/acme/jobs/123",
        company_name="Acme Corp",
        job_title="AI Trainer",
        normalized_job_title="AI Trainer",
        job_description_clean="Deliver AI training to enterprise customers.",
        location_raw="Remote - Worldwide",
        collection_method=CollectionMethod.ATS,
        content_hash="hash1",
    )
    base.update(overrides)
    return NormalizedJob(**base)


def test_same_source_and_id_is_duplicate():
    a = _job()
    b = _job(job_description_clean="slightly different text now", content_hash="hash2")
    assert is_duplicate(a, b) is True


def test_same_content_hash_is_duplicate():
    a = _job(source="lever", source_job_id="999")
    b = _job(source="greenhouse", source_job_id="123")
    assert is_duplicate(a, b) is True


def test_different_company_is_not_duplicate():
    a = _job()
    b = _job(company_name="Other Company", source_job_id="456", content_hash="hash2")
    assert is_duplicate(a, b) is False


def test_fuzzy_title_match_same_company_same_location_is_duplicate():
    a = _job(source="linkedin", source_job_id="agg-1", content_hash="hashA")
    b = _job(
        source="greenhouse", source_job_id="123",
        job_title="AI Trainer (Remote)", normalized_job_title="AI Trainer",
        content_hash="hashB",
    )
    assert is_duplicate(a, b) is True


def test_different_location_same_title_not_duplicate():
    a = _job(location_raw="Remote - Worldwide", content_hash="hashA", source_job_id="1")
    b = _job(location_raw="Remote - United States only", content_hash="hashB", source_job_id="2")
    assert is_duplicate(a, b) is False


def test_official_ats_source_not_overwritten_by_aggregator():
    assert should_overwrite(existing_source_type="official_ats", new_source_type="aggregator") is False


def test_aggregator_overwritten_by_official_ats():
    assert should_overwrite(existing_source_type="aggregator", new_source_type="official_ats") is True


def test_classify_change_new_updated_duplicate():
    assert classify_change(False, None, "hash1") == "new"
    assert classify_change(True, "hash1", "hash1") == "duplicate"
    assert classify_change(True, "hash1", "hash2") == "updated"
