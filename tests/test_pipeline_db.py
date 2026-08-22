"""End-to-end pipeline + database persistence tests (spec §58 "database
persistence"). Collectors are monkeypatched so this never hits the network."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from jobintel.collectors.base import JobSource
from jobintel.models.enums import CollectionMethod
from jobintel.models.schemas import RawJob


class FakeSource(JobSource):
    """Subclasses the real JobSource interface on purpose: a duck-typed
    stand-in would silently miss interface additions (source_type /
    quality_rank provenance), which is exactly the fixture-drift class of
    bug recorded in IMPLEMENTATION_PLAN.md §7."""

    name = "fake:acme"

    def __init__(self, jobs):
        self._jobs = jobs

    async def discover(self):
        return self._jobs

    async def fetch_details(self, job):
        from jobintel.models.schemas import RawJobDetails
        return RawJobDetails(
            raw_job=job,
            description_text=job.raw_payload.get("description_text", ""),
            published_at=job.updated_at,
        )


def _raw_job(job_id="1", title="Generative AI Trainer", location="Remote - Worldwide", description=None):
    description = description or (
        "Remote worldwide AI training role. Work from anywhere. Deliver "
        "generative AI enablement and prompt engineering training to "
        "enterprise customers."
    )
    return RawJob(
        source="fake",
        source_job_id=job_id,
        source_url=f"https://example.com/jobs/{job_id}",
        company_name="Acme AI",
        job_title=title,
        location_raw=location,
        updated_at=datetime.now(UTC),
        collection_method=CollectionMethod.ATS,
        raw_payload={"description_text": description},
    )


@pytest.mark.asyncio
async def test_collection_persists_new_job(temp_db, monkeypatch):
    from jobintel import pipeline

    fake = FakeSource([_raw_job()])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [fake])

    summary = await pipeline.run_collection()
    assert summary.new_canonical_opportunities == 1
    assert summary.raw_opportunities == 1

    from jobintel.db.models import Job
    with temp_db.session_scope() as session:
        jobs = session.query(Job).all()
        assert len(jobs) == 1
        assert jobs[0].company_name == "Acme AI"
        assert jobs[0].remote_classification == "REMOTE_WORLDWIDE"
        assert jobs[0].candidate_geographically_eligible == "YES"


@pytest.mark.asyncio
async def test_collection_is_idempotent_on_rerun(temp_db, monkeypatch):
    from jobintel import pipeline

    fake = FakeSource([_raw_job()])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [fake])

    await pipeline.run_collection()
    summary2 = await pipeline.run_collection()

    assert summary2.new_canonical_opportunities == 0
    assert summary2.duplicate_opportunities == 1

    from jobintel.db.models import Job
    with temp_db.session_scope() as session:
        assert session.query(Job).count() == 1


@pytest.mark.asyncio
async def test_one_broken_source_does_not_abort_the_run(temp_db, monkeypatch):
    from jobintel import pipeline
    from jobintel.collectors.base import SourceError

    class BrokenSource:
        name = "broken"

        async def discover(self):
            raise SourceError("simulated failure")

    good = FakeSource([_raw_job(job_id="2")])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [BrokenSource(), good])

    summary = await pipeline.run_collection()
    assert summary.errors
    assert summary.new_canonical_opportunities == 1


def test_evaluation_scores_and_stores_analysis(temp_db, monkeypatch):
    import asyncio

    from jobintel import pipeline

    fake = FakeSource([_raw_job()])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [fake])
    asyncio.run(pipeline.run_collection())

    summary = pipeline.run_evaluation()
    assert summary.evaluated == 1

    from jobintel.db.models import JobAnalysisRecord
    with temp_db.session_scope() as session:
        analyses = session.query(JobAnalysisRecord).all()
        assert len(analyses) == 1
        assert analyses[0].overall_score > 0
        assert analyses[0].recommendation in (
            "EXCEPTIONAL_MATCH", "STRONG_APPLY", "WORTH_REVIEWING", "STRETCH_OPPORTUNITY",
        )


def test_evaluation_is_not_rerun_for_already_scored_jobs(temp_db, monkeypatch):
    import asyncio

    from jobintel import pipeline

    fake = FakeSource([_raw_job()])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [fake])
    asyncio.run(pipeline.run_collection())

    pipeline.run_evaluation()
    summary2 = pipeline.run_evaluation()
    assert summary2.evaluated == 0
