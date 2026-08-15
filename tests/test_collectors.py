"""Collector adapter tests against mocked HTTP responses shaped like the
real Greenhouse/Lever/Ashby payloads documented in ARCHITECTURE.md §6."""

from __future__ import annotations

import pytest

from jobintel.collectors.ashby import AshbySource
from jobintel.collectors.base import SourceError
from jobintel.collectors.greenhouse import GreenhouseSource
from jobintel.collectors.lever import LeverSource
from jobintel.collectors.remotive import RemotiveSource


@pytest.mark.asyncio
async def test_greenhouse_discover_parses_jobs(httpx_mock):
    httpx_mock.add_response(
        url="https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true",
        json={
            "jobs": [
                {
                    "id": 111,
                    "title": "AI Trainer",
                    "updated_at": "2026-08-10T12:00:00Z",
                    "location": {"name": "Remote - Worldwide"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/111",
                }
            ],
            "meta": {"total": 1},
        },
    )
    source = GreenhouseSource("Acme", "acme")
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"
    assert jobs[0].source_job_id == "111"
    assert jobs[0].job_title == "AI Trainer"
    assert jobs[0].location_raw == "Remote - Worldwide"


@pytest.mark.asyncio
async def test_greenhouse_404_raises_source_error(httpx_mock):
    httpx_mock.add_response(
        url="https://boards-api.greenhouse.io/v1/boards/badtoken/jobs?content=true",
        status_code=404,
    )
    source = GreenhouseSource("Acme", "badtoken")
    with pytest.raises(SourceError):
        await source.discover()


@pytest.mark.asyncio
async def test_lever_discover_parses_postings(httpx_mock):
    httpx_mock.add_response(
        url="https://api.lever.co/v0/postings/acme?mode=json",
        json=[
            {
                "id": "abc-123",
                "text": "Generative AI Trainer",
                "categories": {"location": "Remote - EMEA"},
                "hostedUrl": "https://jobs.lever.co/acme/abc-123",
                "createdAt": 1754899200000,
            }
        ],
    )
    source = LeverSource("Acme", "acme")
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source == "lever"
    assert jobs[0].job_title == "Generative AI Trainer"
    assert jobs[0].location_raw == "Remote - EMEA"


@pytest.mark.asyncio
async def test_ashby_discover_parses_jobs(httpx_mock):
    httpx_mock.add_response(
        url="https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true",
        json={
            "jobs": [
                {
                    "id": "job-1",
                    "title": "AI Security Specialist",
                    "location": "Remote - UK",
                    "publishedAt": "2026-08-09T08:00:00.000Z",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
                }
            ]
        },
    )
    source = AshbySource("Acme", "acme")
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source == "ashby"
    assert jobs[0].job_title == "AI Security Specialist"
    assert jobs[0].location_raw == "Remote - UK"


@pytest.mark.asyncio
async def test_remotive_discover_parses_jobs_with_per_job_company(httpx_mock):
    """Remotive is a multi-employer aggregator: company_name comes from
    each job in the payload, not from a fixed source-level company."""
    httpx_mock.add_response(
        url="https://remotive.com/api/remote-jobs?limit=100&search=cybersecurity",
        json={
            "jobs": [
                {
                    "id": 987654,
                    "url": "https://remotive.com/remote-jobs/cybersecurity/987654",
                    "title": "Remote Cybersecurity Trainer",
                    "company_name": "Acme Security Co",
                    "candidate_required_location": "Worldwide",
                    "publication_date": "2026-08-01T00:00:00",
                    "salary": "$50,000 - $70,000",
                    "description": "<p>Train our global customers on secure AI usage.</p>",
                }
            ]
        },
    )
    source = RemotiveSource("Remotive - Cybersecurity", "cybersecurity")
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source == "remotive"
    assert jobs[0].company_name == "Acme Security Co"
    assert jobs[0].job_title == "Remote Cybersecurity Trainer"
    assert jobs[0].location_raw == "Worldwide"

    details = await source.fetch_details(jobs[0])
    assert details.salary_raw == "$50,000 - $70,000"
    assert "secure AI usage" in details.description_html


@pytest.mark.asyncio
async def test_remotive_unfiltered_search_omits_search_param(httpx_mock):
    httpx_mock.add_response(
        url="https://remotive.com/api/remote-jobs?limit=100",
        json={"jobs": []},
    )
    source = RemotiveSource("Remotive - All", "")
    jobs = await source.discover()
    assert jobs == []


@pytest.mark.asyncio
async def test_remotive_500_raises_source_error(httpx_mock):
    httpx_mock.add_response(
        url="https://remotive.com/api/remote-jobs?limit=100&search=nonsense",
        status_code=500,
    )
    source = RemotiveSource("Remotive - Broken", "nonsense")
    with pytest.raises(SourceError):
        await source.discover()


@pytest.mark.asyncio
async def test_greenhouse_fetch_details_extracts_description_from_list_payload():
    """Regression test: fetch_details() must actually populate the
    description from the ?content=true list response - the base class's
    default fetch_details() only echoes raw_payload and leaves
    description_html/description_text empty, which silently starved the
    geography/matching engines of any text to work with in production."""
    from jobintel.models.enums import CollectionMethod
    from jobintel.models.schemas import RawJob

    raw_job = RawJob(
        source="greenhouse", source_job_id="111", source_url="https://boards.greenhouse.io/acme/jobs/111",
        company_name="Acme", job_title="AI Trainer", location_raw="Sydney, Australia",
        collection_method=CollectionMethod.ATS,
        raw_payload={
            "id": 111,
            "content": "&lt;div&gt;&lt;p&gt;Remote worldwide role. Work from anywhere.&lt;/p&gt;&lt;/div&gt;",
            "first_published": "2026-08-01T00:00:00Z",
        },
    )
    source = GreenhouseSource("Acme", "acme")
    details = await source.fetch_details(raw_job)
    assert details.description_html
    assert "Remote worldwide" in details.description_html or "&lt;" in details.description_html
    assert details.published_at is not None


@pytest.mark.asyncio
async def test_lever_fetch_details_extracts_description_and_salary():
    from jobintel.models.enums import CollectionMethod
    from jobintel.models.schemas import RawJob

    raw_job = RawJob(
        source="lever", source_job_id="abc-123", source_url="https://jobs.lever.co/acme/abc-123",
        company_name="Acme", job_title="AI Trainer",
        collection_method=CollectionMethod.ATS,
        raw_payload={
            "id": "abc-123",
            "descriptionPlain": "Remote worldwide AI training role.",
            "salaryRange": {"min": 80000, "max": 100000, "currency": "USD", "interval": "year"},
        },
    )
    source = LeverSource("Acme", "acme")
    details = await source.fetch_details(raw_job)
    assert details.description_text == "Remote worldwide AI training role."
    assert details.salary_raw and "80000" in details.salary_raw


@pytest.mark.asyncio
async def test_ashby_fetch_details_extracts_description():
    from jobintel.models.enums import CollectionMethod
    from jobintel.models.schemas import RawJob

    raw_job = RawJob(
        source="ashby", source_job_id="job-1", source_url="https://jobs.ashbyhq.com/acme/job-1",
        company_name="Acme", job_title="AI Security Specialist",
        collection_method=CollectionMethod.ATS,
        raw_payload={
            "id": "job-1",
            "descriptionPlain": "Remote UK AI security role.",
            "descriptionHtml": "<p>Remote UK AI security role.</p>",
            "publishedAt": "2026-08-09T08:00:00.000Z",
        },
    )
    source = AshbySource("Acme", "acme")
    details = await source.fetch_details(raw_job)
    assert details.description_text == "Remote UK AI security role."
    assert details.published_at is not None


@pytest.mark.asyncio
async def test_source_error_does_not_propagate_as_unhandled_exception(httpx_mock):
    """One broken source must never abort a whole run (spec §57) - this
    is enforced at the orchestration layer in jobintel.pipeline, which
    catches SourceError per-source; here we just confirm the adapter
    raises the typed error rather than letting a raw httpx exception
    escape uncaught."""
    httpx_mock.add_response(
        url="https://api.lever.co/v0/postings/broken?mode=json",
        status_code=500,
    )
    source = LeverSource("Broken Co", "broken")
    with pytest.raises(SourceError):
        await source.discover()
