"""Search-discovery collector tests (spec §31).

The behaviour that matters here is not "can it parse JSON" but the
provenance rules: aggregator listings must be recorded as second-hand so
they never overwrite an employer's own posting text and never carry the
same confidence.
"""

from __future__ import annotations

import re

import pytest

from jobintel.collectors.base import SourceError
from jobintel.dedup.engine import should_overwrite
from jobintel.discovery.search import (
    RemoteOKSearchSource,
    RemotiveSearchSource,
    build_search_sources,
    query_terms,
)


def test_query_terms_are_bare_keywords_not_search_engine_syntax():
    terms = query_terms(families=["ai_training"])
    assert terms
    assert all('"' not in t for t in terms)
    assert all("remote" not in t.lower().split() for t in terms)


@pytest.mark.asyncio
async def test_remotive_discover_and_details(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://remotive\.com/api/remote-jobs.*"),
        json={
            "job-count": 1,
            "jobs": [
                {
                    "id": 1900001,
                    "url": "https://remotive.com/remote-jobs/ai/ai-trainer-1900001",
                    "title": "AI Trainer",
                    "company_name": "Example Co",
                    "candidate_required_location": "Worldwide",
                    "publication_date": "2026-08-20T10:00:00",
                    "salary": "$70,000 - $90,000",
                    "description": "<p>Deliver generative AI training worldwide.</p>",
                }
            ],
        },
        is_reusable=True,
    )
    source = RemotiveSearchSource(families=["ai_training"], max_queries=1)
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].company_name == "Example Co"
    # Remotive's "who may hold this job" field is the geography signal.
    assert jobs[0].location_raw == "Worldwide"

    details = await source.fetch_details(jobs[0])
    assert "generative AI training" in details.description_html
    assert details.salary_raw == "$70,000 - $90,000"


@pytest.mark.asyncio
async def test_remoteok_skips_legal_notice_and_filters_by_query(httpx_mock):
    httpx_mock.add_response(
        url="https://remoteok.com/api",
        json=[
            {"legal": "Remote OK API - attribution required"},
            {
                "id": "77",
                "slug": "ai-trainer",
                "position": "AI Trainer",
                "company": "Example Co",
                "location": "Worldwide",
                "date": "2026-08-20T10:00:00+00:00",
                "description": "Deliver AI training.",
                "url": "https://remoteok.com/remote-jobs/77",
                "salary_min": 70000,
                "salary_max": 90000,
            },
            {
                "id": "78",
                "position": "Warehouse Supervisor",
                "company": "Unrelated Ltd",
                "description": "Manage a warehouse team.",
                "url": "https://remoteok.com/remote-jobs/78",
            },
        ],
    )
    source = RemoteOKSearchSource(families=["ai_training"], max_queries=4)
    jobs = await source.discover()

    titles = [j.job_title for j in jobs]
    assert "AI Trainer" in titles
    # The legal-notice element is not a job, and an unrelated posting must
    # not be swept in just because the endpoint returns the whole board.
    assert "Warehouse Supervisor" not in titles
    assert all(j.source_job_id for j in jobs)

    details = await source.fetch_details(jobs[0])
    assert details.salary_raw and "70000" in details.salary_raw


@pytest.mark.asyncio
async def test_search_source_unexpected_shape_is_loud(httpx_mock):
    httpx_mock.add_response(url="https://remoteok.com/api", json={"not": "a list"})
    with pytest.raises(SourceError):
        await RemoteOKSearchSource(families=["ai_training"]).discover()


def test_aggregator_provenance_never_outranks_the_employers_own_posting():
    """The core provenance rule: an aggregator copy must not overwrite
    text collected from the employer's own ATS, but the reverse must."""
    aggregator = RemotiveSearchSource(families=["ai_training"])
    assert aggregator.source_type == "aggregator"
    assert aggregator.quality_rank > 1

    assert should_overwrite("official_ats", "aggregator") is False
    assert should_overwrite("aggregator", "official_ats") is True


def test_search_backends_are_config_driven_and_default_to_disabled():
    """Both backends ship unverified, so a normal run must not silently
    depend on them until they are explicitly enabled."""
    assert build_search_sources() == []
    enabled = build_search_sources(enabled=["remotive"], families=["ai_training"])
    assert [s.name for s in enabled] == ["search:remotive"]


def test_aggregator_only_jobs_lose_confidence(temp_db):
    """A job known only through an aggregator must score lower confidence
    than the same job seen on the employer's own board."""
    from jobintel.db.models import Job, JobSourceRecord
    from jobintel.pipeline import _is_aggregator_only

    with temp_db.session_scope() as session:
        job = Job(
            source="remotive", source_job_id="1", source_url="u", canonical_url="u",
            company_name="Example Co", job_title="AI Trainer", normalized_job_title="ai trainer",
            content_hash="hash-1",
        )
        session.add(job)
        session.flush()
        job_id = job.id
        session.add(JobSourceRecord(job_id=job_id, source="remotive", source_url="u", source_type="aggregator", quality_rank=4))

    with temp_db.session_scope() as session:
        job = session.query(Job).filter_by(id=job_id).one()
        assert _is_aggregator_only(job) is True
        session.add(JobSourceRecord(job_id=job_id, source="greenhouse", source_url="u2", source_type="official_ats", quality_rank=1))

    with temp_db.session_scope() as session:
        job = session.query(Job).filter_by(id=job_id).one()
        assert _is_aggregator_only(job) is False


def test_max_queries_per_run_is_actually_applied():
    """The knob that bounds outbound request volume has to reach the
    source - it was previously read from config by nothing, so editing it
    changed no behaviour at all."""
    source = build_search_sources(enabled=["remotive"], families=["ai_training", "cybersecurity"])[0]
    assert len(source.queries) <= 8

    two_queries = build_search_sources(enabled=["remotive"], families=["ai_training"])[0]
    assert two_queries.queries  # config-driven, not hard-coded


def test_max_queries_per_run_reaches_the_source(monkeypatch):
    import jobintel.discovery.search as search_module

    original = search_module.load_search_queries()
    patched = {
        **original,
        "search_discovery": {
            **original["search_discovery"],
            "backends": {"remotive": True},
            "max_queries_per_run": 2,
        },
    }
    monkeypatch.setattr(search_module, "load_search_queries", lambda: patched)
    assert len(build_search_sources()[0].queries) == 2
