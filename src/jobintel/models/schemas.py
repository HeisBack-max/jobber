"""Pydantic schemas for the collection/normalization/analysis pipeline.

These are the in-memory contracts between pipeline stages. The
SQLAlchemy models in jobintel.db.models are the persisted equivalent -
keeping them separate lets normalization/scoring be unit tested with no
database at all.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from jobintel.models.enums import (
    CollectionMethod,
    EligibilityStatus,
    EmploymentType,
    OpportunityClass,
    Recommendation,
    RemoteClassification,
    SeniorityLevel,
)


class RawJob(BaseModel):
    """Minimal identity of a job as returned by a source's listing endpoint."""

    source: str
    source_job_id: str
    source_url: str
    company_name: str
    job_title: str
    location_raw: str | None = None
    updated_at: datetime | None = None
    collection_method: CollectionMethod
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class RawJobDetails(BaseModel):
    """Full detail payload fetched for a single RawJob."""

    raw_job: RawJob
    description_html: str | None = None
    description_text: str | None = None
    salary_raw: str | None = None
    published_at: datetime | None = None
    application_deadline: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class GeographicEvidence(BaseModel):
    classification: RemoteClassification
    eligible: EligibilityStatus
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    required_residence_countries: list[str] = Field(default_factory=list)
    permitted_residence_countries: list[str] = Field(default_factory=list)
    excluded_residence_countries: list[str] = Field(default_factory=list)
    us_presence_required: bool = False
    thailand_presence_required: bool = False
    travel_required: bool = False
    travel_frequency: str | None = None
    travel_destinations: list[str] = Field(default_factory=list)
    physical_office_requirement: bool = False
    office_country: str | None = None
    timezone_requirements: str | None = None


class NormalizedJob(BaseModel):
    """Canonical opportunity schema - mirrors spec §33 field-for-field."""

    source: str
    source_job_id: str
    source_url: str
    canonical_url: str
    company_name: str
    company_domain: str | None = None
    job_title: str
    normalized_job_title: str
    role_family: str | None = None
    opportunity_class: OpportunityClass = OpportunityClass.PERMANENT_EMPLOYMENT
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    contract_type: str | None = None

    job_description_raw: str | None = None
    job_description_clean: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_experience: str | None = None
    education_requirements: list[str] = Field(default_factory=list)
    certification_requirements: list[str] = Field(default_factory=list)
    language_requirements: list[str] = Field(default_factory=list)
    security_clearance_requirements: list[str] = Field(default_factory=list)

    location_raw: str | None = None
    remote_classification: RemoteClassification = RemoteClassification.UNCLEAR
    location_eligibility: EligibilityStatus = EligibilityStatus.UNCLEAR
    required_residence_countries: list[str] = Field(default_factory=list)
    permitted_residence_countries: list[str] = Field(default_factory=list)
    excluded_residence_countries: list[str] = Field(default_factory=list)
    timezone_requirements: str | None = None
    travel_required: bool = False
    travel_frequency: str | None = None
    travel_destinations: list[str] = Field(default_factory=list)
    physical_office_requirement: bool = False
    office_country: str | None = None
    work_authorization_required: bool = False
    visa_requirements: str | None = None
    us_presence_required: bool = False
    thailand_presence_required: bool = False
    candidate_geographically_eligible: EligibilityStatus = EligibilityStatus.UNCLEAR
    geographic_evidence: list[str] = Field(default_factory=list)
    geographic_confidence: float = 0.5

    salary_raw: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None

    published_at: datetime | None = None
    updated_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    application_deadline: datetime | None = None
    is_active: bool = True

    seniority: SeniorityLevel = SeniorityLevel.UNSPECIFIED
    collection_method: CollectionMethod = CollectionMethod.API
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None


class JobAnalysis(BaseModel):
    """Structured analysis output - mirrors spec §34."""

    profile_version: str
    remote_score: float
    experience_score: float
    skills_score: float
    training_advantage_score: float
    ai_cyber_intersection_score: float
    interview_probability_score: float
    compensation_score: float
    freshness_score: float
    strategic_company_bonus: float = 0.0
    can_do_score: float
    interview_probability_score_overall: float
    desirability_score: float
    overall_score: float
    confidence_score: float
    recommendation: Recommendation
    mandatory_mismatches: list[str] = Field(default_factory=list)
    preferred_gaps: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    geographic_evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    application_readiness: str = "NOT_RECOMMENDED"
    model_used: str = "deterministic"
    prompt_version: str = "v1"
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandidateProfile(BaseModel):
    name: str
    positioning: str
    preferred_role_families: list[str]
    excluded_required_work_countries: list[str]
    excluded_relocation_countries: list[str]
    excluded_regular_travel_countries: list[str]
    remote_priority: list[str]
