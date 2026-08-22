"""Adapter tests for the non-Greenhouse/Lever/Ashby collectors added to
close the "employers without a public ATS board" gap
(IMPLEMENTATION_PLAN.md §1).

Payload fixtures are shaped like the real responses documented in each
adapter's module docstring. Per the fixture-drift lesson in §7, every
test asserts on the *description* actually reaching RawJobDetails, not
just on the listing parse - an adapter that discovers jobs but returns
empty descriptions starves the geography and matching engines and looks
like "everything is UNCLEAR" downstream.
"""

from __future__ import annotations

import re

import pytest

from jobintel.collectors.base import SourceError
from jobintel.collectors.careersite import AmazonJobsSource, GoogleCareersSource, MicrosoftCareersSource, default_query_terms
from jobintel.collectors.recruitee import RecruiteeSource
from jobintel.collectors.smartrecruiters import SmartRecruitersSource
from jobintel.collectors.workable import WorkableSource
from jobintel.collectors.workday import WorkdaySource, parse_workday_token

WORKDAY_BASE = "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/AcmeCareers"


# --------------------------------------------------------------------------
# Workday
# --------------------------------------------------------------------------

def test_workday_token_parsing_accepts_short_form_and_full_url():
    assert parse_workday_token("acme.wd5/AcmeCareers") == ("acme", "wd5", "AcmeCareers")
    assert parse_workday_token("https://acme.wd5.myworkdayjobs.com/AcmeCareers") == ("acme", "wd5", "AcmeCareers")
    assert parse_workday_token("https://acme.wd5.myworkdayjobs.com/en-US/AcmeCareers") == ("acme", "wd5", "AcmeCareers")


def test_workday_token_parsing_rejects_garbage_loudly():
    """A malformed token must fail as a typed SourceError at build time -
    not silently produce a URL that 404s and reads as "no jobs today"."""
    with pytest.raises(SourceError):
        parse_workday_token("nvidia-careers")


@pytest.mark.asyncio
async def test_workday_discover_and_fetch_details(httpx_mock):
    httpx_mock.add_response(
        url=f"{WORKDAY_BASE}/jobs",
        method="POST",
        json={
            "total": 1,
            "jobPostings": [
                {
                    "title": "AI Enablement Specialist",
                    "externalPath": "/job/Remote-UK/AI-Enablement-Specialist_JR123",
                    "locationsText": "Remote, United Kingdom",
                    "postedOn": "Posted 3 Days Ago",
                    "bulletFields": ["JR123"],
                }
            ],
        },
    )
    httpx_mock.add_response(
        url=f"{WORKDAY_BASE}/job/Remote-UK/AI-Enablement-Specialist_JR123",
        json={
            "jobPostingInfo": {
                "jobDescription": "<p>Deliver AI enablement training to enterprise customers.</p>",
                "startDate": "2026-08-19",
                "location": "Remote, United Kingdom",
                "remoteType": "Remote",
            }
        },
    )

    source = WorkdaySource("Acme", "acme.wd5/AcmeCareers")
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source_job_id == "JR123"
    assert jobs[0].location_raw == "Remote, United Kingdom"
    assert jobs[0].updated_at is not None  # "Posted 3 Days Ago" is parseable

    details = await source.fetch_details(jobs[0])
    assert "AI enablement training" in details.description_html
    # remoteType is a structured Workday field that never appears in the
    # description HTML; without it the geography classifier would only
    # ever see the location string.
    assert "Remote" in details.description_html
    assert details.published_at is not None


@pytest.mark.asyncio
async def test_workday_unposted_date_is_unknown_not_now():
    """An unparseable "postedOn" must stay None. Guessing "now" would
    hand an old posting a perfect freshness score."""
    from jobintel.collectors.workday import _posted_on_to_dt

    assert _posted_on_to_dt("Posted Some Time Ago") is None
    assert _posted_on_to_dt(None) is None
    assert _posted_on_to_dt("Posted Today") is not None


@pytest.mark.asyncio
async def test_workday_404_raises_source_error(httpx_mock):
    httpx_mock.add_response(url=f"{WORKDAY_BASE}/jobs", method="POST", status_code=404)
    source = WorkdaySource("Acme", "acme.wd5/AcmeCareers")
    with pytest.raises(SourceError):
        await source.discover()


# --------------------------------------------------------------------------
# SmartRecruiters
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_smartrecruiters_discover_and_details(httpx_mock):
    httpx_mock.add_response(
        url="https://api.smartrecruiters.com/v1/companies/acme/postings?limit=100&offset=0",
        json={
            "totalFound": 1,
            "content": [
                {
                    "id": "744000",
                    "name": "Cybersecurity Trainer",
                    "releasedDate": "2026-08-18T09:00:00.000Z",
                    "location": {"city": "London", "country": "uk", "remote": True},
                    "applyUrl": "https://jobs.smartrecruiters.com/acme/744000",
                }
            ],
        },
    )
    httpx_mock.add_response(
        url="https://api.smartrecruiters.com/v1/companies/acme/postings/744000",
        json={
            "jobAd": {
                "sections": {
                    "jobDescription": {"title": "Job Description", "text": "<p>Deliver cybersecurity training.</p>"},
                    "qualifications": {"title": "Qualifications", "text": "<p>OSINT and GRC instruction experience.</p>"},
                }
            }
        },
    )

    source = SmartRecruitersSource("Acme", "acme")
    jobs = await source.discover()
    assert len(jobs) == 1
    # `remote` is a boolean field, not part of the location string - it
    # must be surfaced into location_raw or the geography engine loses it.
    assert jobs[0].location_raw.startswith("Remote")

    details = await source.fetch_details(jobs[0])
    assert "cybersecurity training" in details.description_html
    assert "OSINT" in details.description_html


@pytest.mark.asyncio
async def test_smartrecruiters_404_raises_source_error(httpx_mock):
    httpx_mock.add_response(
        url="https://api.smartrecruiters.com/v1/companies/nope/postings?limit=100&offset=0",
        status_code=404,
    )
    with pytest.raises(SourceError):
        await SmartRecruitersSource("Nope", "nope").discover()


# --------------------------------------------------------------------------
# Workable / Recruitee
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workable_discover_includes_description_in_one_request(httpx_mock):
    httpx_mock.add_response(
        url="https://apply.workable.com/api/v1/widget/accounts/acme?details=true",
        json={
            "name": "Acme",
            "jobs": [
                {
                    "title": "AI Trainer",
                    "shortcode": "ABC123",
                    "url": "https://apply.workable.com/acme/j/ABC123/",
                    "telecommuting": True,
                    "city": "Berlin",
                    "country": "Germany",
                    "published_on": "2026-08-15",
                    "description": "<p>Train enterprise teams on generative AI.</p>",
                    "requirements": "<p>Instructional design experience.</p>",
                }
            ],
        },
    )
    source = WorkableSource("Acme", "acme")
    jobs = await source.discover()
    assert jobs[0].source_job_id == "ABC123"
    assert jobs[0].location_raw.startswith("Remote")

    details = await source.fetch_details(jobs[0])
    assert "generative AI" in details.description_html
    assert "Instructional design" in details.description_html


@pytest.mark.asyncio
async def test_recruitee_discover_includes_description_in_one_request(httpx_mock):
    httpx_mock.add_response(
        url="https://acme.recruitee.com/api/offers/",
        json={
            "offers": [
                {
                    "id": 987,
                    "title": "Technical Instructional Designer",
                    "description": "<p>Design technical curriculum.</p>",
                    "requirements": "<p>Adult learning background.</p>",
                    "location": "Remote - Europe",
                    "careers_url": "https://acme.recruitee.com/o/technical-instructional-designer",
                    "published_at": "2026-08-12T10:00:00.000+00:00",
                    "remote": True,
                }
            ]
        },
    )
    source = RecruiteeSource("Acme", "acme")
    jobs = await source.discover()
    assert jobs[0].source_job_id == "987"

    details = await source.fetch_details(jobs[0])
    assert "technical curriculum" in details.description_html
    assert "Adult learning" in details.description_html


# --------------------------------------------------------------------------
# Career-site collectors (Microsoft / Amazon / Google)
# --------------------------------------------------------------------------

def test_default_query_terms_are_derived_from_search_queries_config():
    terms = default_query_terms()
    assert terms
    # The configured queries are search-engine syntax ('"AI trainer" remote');
    # these APIs take bare keywords, so quoting and the "remote"/"jobs"
    # noise words must be stripped.
    assert all('"' not in t for t in terms)
    assert all(not t.lower().endswith(" remote") for t in terms)


@pytest.mark.asyncio
async def test_microsoft_career_site_discover_and_details(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://gcsservices\.careers\.microsoft\.com/search/api/v1/search.*"),
        json={
            "operationResult": {
                "result": {
                    "totalJobs": 1,
                    "jobs": [
                        {
                            "jobId": "1800000",
                            "title": "AI Technical Trainer",
                            "postingDate": "2026-08-20T00:00:00+00:00",
                            "properties": {"primaryLocation": "London, United Kingdom", "workSiteFlexibility": "Up to 100% work from home"},
                        }
                    ],
                }
            }
        },
        is_reusable=True,
    )
    httpx_mock.add_response(
        url=re.compile(r"https://gcsservices\.careers\.microsoft\.com/search/api/v1/job/1800000.*"),
        json={
            "operationResult": {
                "result": {
                    "postingDate": "2026-08-20T00:00:00+00:00",
                    "properties": {
                        "description": "Deliver AI training to enterprise customers.",
                        "qualifications": "Technical training experience.",
                        "workSiteFlexibility": "Up to 100% work from home",
                    },
                }
            }
        },
    )

    source = MicrosoftCareersSource(queries=["AI trainer"])
    jobs = await source.discover()
    assert len(jobs) == 1
    assert jobs[0].source == "microsoft"
    assert "work from home" in jobs[0].location_raw

    details = await source.fetch_details(jobs[0])
    assert "AI training" in details.description_html


@pytest.mark.asyncio
async def test_career_site_unexpected_payload_shape_is_loud(httpx_mock):
    """An upstream API change must surface as BROKEN in source health, not
    as a silent "0 jobs" that quietly hides a whole employer."""
    httpx_mock.add_response(
        url=re.compile(r"https://gcsservices\.careers\.microsoft\.com/search/api/v1/search.*"),
        json={"unexpected": "shape"},
    )
    with pytest.raises(SourceError):
        await MicrosoftCareersSource(queries=["AI trainer"]).discover()


@pytest.mark.asyncio
async def test_amazon_career_site_discover_and_details(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://www\.amazon\.jobs/en/search\.json.*"),
        json={
            "hits": 1,
            "jobs": [
                {
                    "id_icims": "2900000",
                    "title": "AI Enablement Consultant",
                    "job_path": "/en/jobs/2900000/ai-enablement-consultant",
                    "normalized_location": "Remote, United Kingdom",
                    "posted_date": "August 18, 2026",
                    "description": "Enable customers to adopt generative AI.",
                    "basic_qualifications": "Training delivery experience.",
                }
            ],
        },
    )
    source = AmazonJobsSource(queries=["AI enablement"])
    jobs = await source.discover()
    assert jobs[0].source_url.startswith("https://www.amazon.jobs/en/jobs/")
    assert jobs[0].updated_at is not None  # "August 18, 2026" must parse

    details = await source.fetch_details(jobs[0])
    assert "generative AI" in details.description_html
    assert "Training delivery" in details.description_html


@pytest.mark.asyncio
async def test_google_career_site_discover_and_details(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://careers\.google\.com/api/v3/search/.*"),
        json={
            "count": 1,
            "jobs": [
                {
                    "id": "jobs/12345",
                    "title": "Vertex AI Enablement Consultant",
                    "summary": "Train customers on Vertex AI and Gemini.",
                    "description": "Deliver Google Cloud generative AI enablement.",
                    "locations": [{"display": "London, UK"}],
                    "publish_date": "2026-08-17",
                    "apply_url": "https://www.google.com/about/careers/applications/jobs/results/12345",
                }
            ],
        },
    )
    source = GoogleCareersSource(queries=["Vertex AI trainer"])
    jobs = await source.discover()
    assert jobs[0].source_job_id == "12345"
    assert jobs[0].location_raw == "London, UK"

    details = await source.fetch_details(jobs[0])
    assert "Vertex AI" in details.description_html


# --------------------------------------------------------------------------
# Registry wiring
# --------------------------------------------------------------------------

def test_registry_builds_every_supported_ats():
    from jobintel.discovery.registry import SUPPORTED_ATS, build_source_for

    tokens = {
        "greenhouse": "acme", "lever": "acme", "ashby": "acme",
        "workday": "acme.wd5/AcmeCareers", "smartrecruiters": "acme",
        "workable": "acme", "recruitee": "acme",
        "careersite_microsoft": "microsoft", "careersite_amazon": "amazon",
        "careersite_google": "google",
    }
    assert set(tokens) == set(SUPPORTED_ATS)
    for ats, token in tokens.items():
        source = build_source_for(ats, "Acme", token, {})
        assert source is not None, ats
        assert source.name
        assert source.source_type in {"official_ats", "official_employer", "aggregator"}


def test_registry_skips_muted_entries_but_still_lists_them_for_verification():
    """Muted entries must be verifiable (that is how a new board gets
    promoted) while never being polled by a normal collection run."""
    from jobintel.discovery.registry import build_sources, load_registry_entries

    entries = load_registry_entries()
    muted = [e for e in entries if not e.is_polled]
    assert muted, "expected at least one muted, ships-but-unverified entry"

    polled_names = {s.name for s in build_sources()}
    for entry in muted:
        assert not any(entry.board_token in name for name in polled_names)


def test_every_configured_source_declares_a_supported_ats():
    from jobintel.discovery.registry import SUPPORTED_ATS, load_registry_entries

    for entry in load_registry_entries():
        assert entry.ats in SUPPORTED_ATS, f"{entry.name} uses unsupported ats {entry.ats!r}"
