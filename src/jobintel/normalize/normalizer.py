"""Raw -> canonical NormalizedJob (spec §33)."""

from __future__ import annotations

import hashlib
import re

from jobintel.geography.classifier import classify_geography
from jobintel.geography.eligibility import finalize_eligibility
from jobintel.models.enums import EmploymentType, OpportunityClass
from jobintel.models.schemas import NormalizedJob, RawJobDetails
from jobintel.normalize.clean import strip_html
from jobintel.normalize.salary import parse_salary
from jobintel.normalize.title import detect_seniority, normalize_title

_EMPLOYMENT_TYPE_PATTERNS = [
    (re.compile(r"\bfull[\s-]time\b", re.I), EmploymentType.FULL_TIME),
    (re.compile(r"\bpart[\s-]time\b", re.I), EmploymentType.PART_TIME),
    (re.compile(r"\bcontract(or)?\b", re.I), EmploymentType.CONTRACT),
    (re.compile(r"\bfreelance\b", re.I), EmploymentType.FREELANCE),
    (re.compile(r"\bintern(ship)?\b", re.I), EmploymentType.INTERNSHIP),
]


def compute_content_hash(company_name: str, normalized_title: str, location_raw: str | None, description_clean: str) -> str:
    payload = "|".join([
        company_name.strip().lower(),
        normalized_title.strip().lower(),
        (location_raw or "").strip().lower(),
        description_clean.strip().lower()[:2000],
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _detect_employment_type(text: str) -> EmploymentType:
    for pattern, etype in _EMPLOYMENT_TYPE_PATTERNS:
        if pattern.search(text or ""):
            return etype
    return EmploymentType.UNSPECIFIED


def normalize_job(details: RawJobDetails, opportunity_class: OpportunityClass = OpportunityClass.PERMANENT_EMPLOYMENT) -> NormalizedJob:
    raw = details.raw_job
    description_clean = details.description_text or strip_html(details.description_html)
    normalized_title = normalize_title(raw.job_title)

    geo = classify_geography(raw.location_raw, description_clean)
    final_eligible = finalize_eligibility(geo)

    salary = parse_salary(details.salary_raw)
    content_hash = compute_content_hash(raw.company_name, normalized_title, raw.location_raw, description_clean)

    return NormalizedJob(
        source=raw.source,
        source_job_id=raw.source_job_id,
        source_url=raw.source_url,
        canonical_url=raw.source_url,
        company_name=raw.company_name,
        job_title=raw.job_title,
        normalized_job_title=normalized_title,
        opportunity_class=opportunity_class,
        employment_type=_detect_employment_type(description_clean),
        job_description_raw=details.description_html or details.description_text,
        job_description_clean=description_clean,
        location_raw=raw.location_raw,
        remote_classification=geo.classification,
        location_eligibility=final_eligible,
        required_residence_countries=geo.required_residence_countries,
        permitted_residence_countries=geo.permitted_residence_countries,
        excluded_residence_countries=geo.excluded_residence_countries,
        timezone_requirements=geo.timezone_requirements,
        travel_required=geo.travel_required,
        travel_frequency=geo.travel_frequency,
        travel_destinations=geo.travel_destinations,
        physical_office_requirement=geo.physical_office_requirement,
        office_country=geo.office_country,
        us_presence_required=geo.us_presence_required,
        thailand_presence_required=geo.thailand_presence_required,
        candidate_geographically_eligible=final_eligible,
        geographic_evidence=geo.evidence,
        geographic_confidence=geo.confidence,
        salary_raw=details.salary_raw,
        salary_min=salary.salary_min,
        salary_max=salary.salary_max,
        salary_currency=salary.salary_currency,
        salary_period=salary.salary_period,
        published_at=details.published_at or raw.updated_at,
        updated_at=raw.updated_at,
        application_deadline=details.application_deadline,
        seniority=detect_seniority(raw.job_title),
        collection_method=raw.collection_method,
        raw_payload=details.raw_payload or raw.raw_payload,
        content_hash=content_hash,
    )
