"""SQLAlchemy ORM models. See IMPLEMENTATION_PLAN.md §4 for schema rationale."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobintel.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ats: Mapped[str | None] = mapped_column(String(50), nullable=True)
    board_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    career_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collection_status: Mapped[str] = mapped_column(String(50), default="normal")
    strategic_themes: Mapped[list] = mapped_column(JSON, default=list)
    verification_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")
    last_successful_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_changed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_health: Mapped[str] = mapped_column(String(30), default="UNKNOWN")

    jobs: Mapped[list[Job]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    source: Mapped[str] = mapped_column(String(50))
    source_job_id: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(1000))
    canonical_url: Mapped[str] = mapped_column(String(1000))

    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    job_title: Mapped[str] = mapped_column(String(500))
    normalized_job_title: Mapped[str] = mapped_column(String(500), index=True)
    role_family: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    opportunity_class: Mapped[str] = mapped_column(String(50), default="PERMANENT_EMPLOYMENT")
    employment_type: Mapped[str] = mapped_column(String(50), default="UNSPECIFIED")
    contract_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    job_description_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_description_clean: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    required_experience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    education_requirements: Mapped[list] = mapped_column(JSON, default=list)
    certification_requirements: Mapped[list] = mapped_column(JSON, default=list)
    language_requirements: Mapped[list] = mapped_column(JSON, default=list)
    security_clearance_requirements: Mapped[list] = mapped_column(JSON, default=list)

    location_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remote_classification: Mapped[str] = mapped_column(String(60), default="UNCLEAR", index=True)
    location_eligibility: Mapped[str] = mapped_column(String(20), default="UNCLEAR")
    required_residence_countries: Mapped[list] = mapped_column(JSON, default=list)
    permitted_residence_countries: Mapped[list] = mapped_column(JSON, default=list)
    excluded_residence_countries: Mapped[list] = mapped_column(JSON, default=list)
    timezone_requirements: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_required: Mapped[bool] = mapped_column(Boolean, default=False)
    travel_frequency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_destinations: Mapped[list] = mapped_column(JSON, default=list)
    physical_office_requirement: Mapped[bool] = mapped_column(Boolean, default=False)
    office_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    work_authorization_required: Mapped[bool] = mapped_column(Boolean, default=False)
    visa_requirements: Mapped[str | None] = mapped_column(String(500), nullable=True)
    us_presence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    thailand_presence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    candidate_geographically_eligible: Mapped[str] = mapped_column(
        String(20), default="UNCLEAR", index=True
    )
    geographic_evidence: Mapped[list] = mapped_column(JSON, default=list)
    geographic_confidence: Mapped[float] = mapped_column(Float, default=0.5)

    salary_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(20), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    seniority: Mapped[str] = mapped_column(String(20), default="unspecified")
    collection_method: Mapped[str] = mapped_column(String(30), default="API")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    company: Mapped[Company | None] = relationship(back_populates="jobs")
    sources: Mapped[list[JobSourceRecord]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    analyses: Mapped[list[JobAnalysisRecord]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    gig: Mapped[Gig | None] = relationship(back_populates="job", uselist=False)
    application_statuses: Mapped[list[ApplicationStatusRecord]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    feedback_entries: Mapped[list[Feedback]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobSourceRecord(Base):
    """Provenance: one canonical job may be discovered through multiple sources."""

    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    source: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(30))  # official_employer, official_ats, aggregator, board
    quality_rank: Mapped[int] = mapped_column(Integer, default=3)  # 1=best (official) .. 5=worst
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job: Mapped[Job] = relationship(back_populates="sources")


class JobAnalysisRecord(Base):
    __tablename__ = "job_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    profile_version: Mapped[str] = mapped_column(String(20), default="v1")

    remote_score: Mapped[float] = mapped_column(Float)
    experience_score: Mapped[float] = mapped_column(Float)
    skills_score: Mapped[float] = mapped_column(Float)
    training_advantage_score: Mapped[float] = mapped_column(Float)
    ai_cyber_intersection_score: Mapped[float] = mapped_column(Float)
    interview_probability_score: Mapped[float] = mapped_column(Float)
    compensation_score: Mapped[float] = mapped_column(Float)
    freshness_score: Mapped[float] = mapped_column(Float)
    strategic_company_bonus: Mapped[float] = mapped_column(Float, default=0.0)

    can_do_score: Mapped[float] = mapped_column(Float)
    desirability_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float, index=True)
    confidence_score: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String(40), index=True)

    mandatory_mismatches: Mapped[list] = mapped_column(JSON, default=list)
    preferred_gaps: Mapped[list] = mapped_column(JSON, default=list)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    concerns: Mapped[list] = mapped_column(JSON, default=list)
    geographic_evidence: Mapped[list] = mapped_column(JSON, default=list)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="")
    application_readiness: Mapped[str] = mapped_column(String(40), default="NOT_RECOMMENDED")

    model_used: Mapped[str] = mapped_column(String(100), default="deterministic")
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job: Mapped[Job] = relationship(back_populates="analyses")


class Gig(Base):
    __tablename__ = "gigs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)

    platform: Mapped[str] = mapped_column(String(100))
    advertised_hourly_rate_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    advertised_hourly_rate_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expected_weekly_hours_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_weekly_hours_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    residency_countries: Mapped[list] = mapped_column(JSON, default=list)
    qualification_requirements: Mapped[list] = mapped_column(JSON, default=list)
    specialist_classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gig_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    job: Mapped[Job] = relationship(back_populates="gig")


class ApplicationStatusRecord(Base):
    __tablename__ = "application_status"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(30), default="New")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recruiter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recruiter_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job: Mapped[Job] = relationship(back_populates="application_statuses")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    reaction: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job: Mapped[Job] = relationship(back_populates="feedback_entries")


class SourceHealthRecord(Base):
    __tablename__ = "source_health"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(100), index=True)
    run_started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    run_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class LlmUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(30), default="stage3")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
