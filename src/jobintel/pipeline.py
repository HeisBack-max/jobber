"""Orchestrates the full pipeline (spec §55): collect -> normalize ->
dedup -> geography -> score -> (optional LLM refine) -> store.

Kept as the one module that touches both the collectors and the
database, so every other package stays independently unit-testable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from jobintel.collectors.base import SourceError
from jobintel.db.models import (
    Gig,
    GigAnalysisRecord,
    Job,
    JobAnalysisRecord,
    JobSourceRecord,
    LlmUsage,
    SourceHealthRecord,
)
from jobintel.db.session import session_scope
from jobintel.dedup.engine import SOURCE_QUALITY_RANK, is_duplicate, should_overwrite
from jobintel.discovery.registry import build_sources
from jobintel.evaluation.evaluator import apply_refinement, get_evaluator
from jobintel.gigs.classifier import classify_gig, platform_reliability_for
from jobintel.matching.career_scorer import score_career_opportunity
from jobintel.matching.cv_evidence import get_evidence_for_categories
from jobintel.matching.gig_scorer import score_gig
from jobintel.matching.role_matcher import semantic_prescore
from jobintel.models.enums import OpportunityClass
from jobintel.models.schemas import NormalizedJob
from jobintel.normalize.normalizer import normalize_job
from jobintel.settings import get_settings, load_scoring, load_strategic_companies

logger = structlog.get_logger()


@dataclass
class CollectionSummary:
    sources_queried: int = 0
    raw_opportunities: int = 0
    new_canonical_opportunities: int = 0
    updated_opportunities: int = 0
    duplicate_opportunities: int = 0
    errors: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (
            "Collection Run Complete\n"
            f"Sources queried: {self.sources_queried}\n"
            f"Raw opportunities: {self.raw_opportunities}\n"
            f"New canonical opportunities: {self.new_canonical_opportunities}\n"
            f"Updated opportunities: {self.updated_opportunities}\n"
            f"Duplicate/repost matches: {self.duplicate_opportunities}\n"
            f"Errors: {len(self.errors)}"
            + ("".join(f"\n  - {e}" for e in self.errors) if self.errors else "")
        )


@dataclass
class EvaluationSummary:
    evaluated: int = 0
    llm_evaluated: int = 0
    strong_matches: int = 0
    exceptional_matches: int = 0
    ineligible: int = 0
    total_llm_cost_usd: float = 0.0
    gigs_identified: int = 0
    high_quality_gigs: int = 0

    def render(self) -> str:
        return (
            "Evaluation Run Complete\n"
            f"Jobs evaluated: {self.evaluated}\n"
            f"LLM-refined: {self.llm_evaluated}\n"
            f"Strong matches: {self.strong_matches}\n"
            f"Exceptional matches: {self.exceptional_matches}\n"
            f"Ineligible (geography): {self.ineligible}\n"
            f"Gigs identified: {self.gigs_identified} "
            f"({self.high_quality_gigs} high quality)\n"
            f"LLM spend this run: ${self.total_llm_cost_usd:.4f}"
        )


def _strategic_company_names() -> set[str]:
    data = load_strategic_companies()
    names = set()
    for tier in data.get("tiers", {}).values():
        for company in tier.get("companies", []):
            names.add(company["name"].strip().lower())
    return names


async def run_collection() -> CollectionSummary:
    summary = CollectionSummary()
    sources = build_sources()
    summary.sources_queried = len(sources)

    with session_scope() as session:
        for source in sources:
            health = SourceHealthRecord(source=source.name, run_started_at=datetime.now(UTC))
            try:
                raw_jobs = await source.discover()
            except SourceError as exc:
                logger.error("pipeline.source_failed", source=source.name, error=str(exc))
                summary.errors.append(f"{source.name}: {exc}")
                health.status = "BROKEN"
                health.errors = [str(exc)]
                health.run_finished_at = datetime.now(UTC)
                session.add(health)
                continue
            except Exception as exc:  # noqa: BLE001 - one source failure must not abort the run
                logger.error("pipeline.source_unexpected_error", source=source.name, error=str(exc))
                summary.errors.append(f"{source.name}: unexpected error: {exc}")
                health.status = "BROKEN"
                health.errors = [str(exc)]
                health.run_finished_at = datetime.now(UTC)
                session.add(health)
                continue

            summary.raw_opportunities += len(raw_jobs)
            health.jobs_discovered = len(raw_jobs)
            health.status = "HEALTHY"
            health.run_finished_at = datetime.now(UTC)
            session.add(health)

            for raw_job in raw_jobs:
                try:
                    details = await source.fetch_details(raw_job)
                    normalized = normalize_job(details)
                    _persist_normalized_job(
                        session, normalized, summary,
                        source_type=source.source_type, quality_rank=source.quality_rank,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error("pipeline.job_processing_failed", source=source.name, error=str(exc))
                    summary.errors.append(f"{source.name}/{raw_job.source_job_id}: {exc}")

    return summary


def _is_aggregator_only(job: Job) -> bool:
    """True when the only place this vacancy has ever been seen is an
    aggregator - which costs confidence (spec §53), because aggregator
    copies are frequently stale, truncated, or stripped of the
    employer's own geography and travel language."""
    records = job.sources
    if not records:
        return False
    return all(r.source_type in {"aggregator", "board", "unknown"} for r in records)


def _best_source_type(job: Job) -> str:
    """The most authoritative source this job has already been seen
    through - an aggregator copy must not overwrite text that came from
    the employer's own ATS (spec §35).

    Reads the loaded `job.sources` relationship rather than issuing its
    own query: in steady state almost every posting from every board
    takes this path on every run, so a query here is thousands of extra
    round-trips per daily run to pick a minimum over a handful of rows.
    """
    records = job.sources
    if not records:
        return "unknown"
    return min(records, key=lambda r: SOURCE_QUALITY_RANK.get(r.source_type, SOURCE_QUALITY_RANK["unknown"])).source_type


def _persist_normalized_job(
    session,
    normalized: NormalizedJob,
    summary: CollectionSummary,
    source_type: str = "official_ats",
    quality_rank: int = 1,
) -> None:
    now = datetime.now(UTC)
    existing = (
        session.query(Job)
        .filter(Job.source == normalized.source, Job.source_job_id == normalized.source_job_id)
        .first()
    )

    if existing is None:
        candidates = session.query(Job).filter(Job.company_name == normalized.company_name).all()
        for candidate in candidates:
            candidate_normalized = NormalizedJob(
                source=candidate.source, source_job_id=candidate.source_job_id,
                source_url=candidate.source_url, canonical_url=candidate.canonical_url,
                company_name=candidate.company_name, job_title=candidate.job_title,
                normalized_job_title=candidate.normalized_job_title,
                job_description_clean=candidate.job_description_clean,
                location_raw=candidate.location_raw, content_hash=candidate.content_hash,
            )
            if is_duplicate(normalized, candidate_normalized):
                existing = candidate
                break

    if existing is None:
        job = Job(
            source=normalized.source, source_job_id=normalized.source_job_id,
            source_url=normalized.source_url, canonical_url=normalized.canonical_url,
            company_name=normalized.company_name, company_domain=normalized.company_domain,
            job_title=normalized.job_title, normalized_job_title=normalized.normalized_job_title,
            opportunity_class=normalized.opportunity_class.value, employment_type=normalized.employment_type.value,
            job_description_raw=normalized.job_description_raw, job_description_clean=normalized.job_description_clean,
            location_raw=normalized.location_raw, remote_classification=normalized.remote_classification.value,
            location_eligibility=normalized.location_eligibility.value,
            required_residence_countries=normalized.required_residence_countries,
            permitted_residence_countries=normalized.permitted_residence_countries,
            excluded_residence_countries=normalized.excluded_residence_countries,
            travel_required=normalized.travel_required, travel_frequency=normalized.travel_frequency,
            travel_destinations=normalized.travel_destinations,
            physical_office_requirement=normalized.physical_office_requirement,
            office_country=normalized.office_country,
            us_presence_required=normalized.us_presence_required,
            thailand_presence_required=normalized.thailand_presence_required,
            candidate_geographically_eligible=normalized.candidate_geographically_eligible.value,
            geographic_evidence=normalized.geographic_evidence,
            geographic_confidence=normalized.geographic_confidence,
            salary_raw=normalized.salary_raw, salary_min=normalized.salary_min, salary_max=normalized.salary_max,
            salary_currency=normalized.salary_currency, salary_period=normalized.salary_period,
            published_at=normalized.published_at, updated_at=normalized.updated_at,
            first_seen_at=now, last_seen_at=now,
            seniority=normalized.seniority.value, collection_method=normalized.collection_method.value,
            raw_payload=normalized.raw_payload, content_hash=normalized.content_hash,
        )
        session.add(job)
        session.flush()
        session.add(JobSourceRecord(
            job_id=job.id, source=normalized.source, source_url=normalized.source_url,
            source_type=source_type, quality_rank=quality_rank,
            source_published_at=normalized.published_at, first_seen_at=now, last_seen_at=now,
        ))
        summary.new_canonical_opportunities += 1
        return

    existing.last_seen_at = now
    best_existing_source_type = _best_source_type(existing)
    if existing.content_hash != normalized.content_hash:
        if should_overwrite(best_existing_source_type, source_type):
            existing.job_description_clean = normalized.job_description_clean
            existing.job_description_raw = normalized.job_description_raw
            existing.salary_raw = normalized.salary_raw
            existing.salary_min = normalized.salary_min
            existing.salary_max = normalized.salary_max
            existing.content_hash = normalized.content_hash
            existing.updated_at = normalized.updated_at
        summary.updated_opportunities += 1
    else:
        summary.duplicate_opportunities += 1

    source_record = (
        session.query(JobSourceRecord)
        .filter_by(job_id=existing.id, source=normalized.source)
        .first()
    )
    if source_record is None:
        session.add(JobSourceRecord(
            job_id=existing.id, source=normalized.source, source_url=normalized.source_url,
            source_type=source_type, quality_rank=quality_rank,
            source_published_at=normalized.published_at, first_seen_at=now, last_seen_at=now,
        ))
    else:
        source_record.last_seen_at = now


def _evaluate_gigs(session, summary: EvaluationSummary, min_quality_score: float) -> None:
    """Identify and score gig/project work among collected postings.

    Runs after career scoring rather than instead of it: a contractor
    posting is still a career opportunity worth ranking, it just also
    needs the gig model, which judges rate, flexibility and duration
    instead of salary and seniority (spec §21).
    """
    scored_job_ids = {row.job_id for row in session.query(Gig).all()}

    for job in session.query(Job).filter(Job.is_active.is_(True)).all():
        if job.id in scored_job_ids:
            continue

        signals = classify_gig(
            job_title=job.job_title,
            description_text=job.job_description_clean,
            employment_type=job.employment_type,
            salary_raw=job.salary_raw,
        )
        if not signals.is_gig:
            continue

        from jobintel.geography.classifier import classify_geography

        geo = classify_geography(job.location_raw, job.job_description_clean)
        result = score_gig(
            title=job.job_title,
            description_text=job.job_description_clean,
            geo_evidence=geo,
            hourly_rate_min=signals.hourly_rate_min,
            hourly_rate_max=signals.hourly_rate_max,
            weekly_hours_min=signals.weekly_hours_min,
            weekly_hours_max=signals.weekly_hours_max,
            platform_reliability=platform_reliability_for(job.company_name),
        )

        gig = Gig(
            job_id=job.id,
            platform=job.company_name,
            advertised_hourly_rate_min=signals.hourly_rate_min,
            advertised_hourly_rate_max=signals.hourly_rate_max,
            rate_currency=signals.rate_currency,
            expected_weekly_hours_min=signals.weekly_hours_min,
            expected_weekly_hours_max=signals.weekly_hours_max,
            project_duration=signals.project_duration,
            residency_countries=geo.required_residence_countries,
            specialist_classification="commodity_annotation" if result.is_commodity_annotation else "specialist",
            gig_quality_score=result.gig_quality_score,
        )
        session.add(gig)
        session.flush()

        session.add(GigAnalysisRecord(
            gig_id=gig.id,
            job_id=job.id,
            gig_quality_score=result.gig_quality_score,
            geographic_compatibility=result.geographic_compatibility,
            professional_relevance=result.professional_relevance,
            compensation=result.compensation,
            flexibility=result.flexibility,
            ai_cyber_career_value=result.ai_cyber_career_value,
            source_reliability=result.source_reliability,
            time_commitment_compatibility=result.time_commitment_compatibility,
            is_commodity_annotation=result.is_commodity_annotation,
            reasoning_summary=(
                f"Classified as gig work ({'; '.join(signals.reasons[:3])}). "
                f"Gig quality {result.gig_quality_score:.1f}/100."
                + (" Commodity annotation work - capped by policy (spec §20)."
                   if result.is_commodity_annotation else "")
            ),
        ))

        job.opportunity_class = OpportunityClass.GIG_PROJECT_WORK.value
        summary.gigs_identified += 1
        if result.gig_quality_score >= min_quality_score:
            summary.high_quality_gigs += 1


def run_evaluation() -> EvaluationSummary:
    return asyncio.run(_run_evaluation_async())


async def _run_evaluation_async() -> EvaluationSummary:
    summary = EvaluationSummary()
    scoring = load_scoring()
    daily_budget = get_settings().daily_llm_budget_usd or scoring["cost_control"]["daily_llm_budget_usd"]
    stage4_threshold = scoring["cost_control"]["stage4_deep_analysis_min_score"]
    stage2_threshold = scoring["cost_control"]["stage2_semantic_prescore_min_to_advance"]
    strategic_names = _strategic_company_names()
    evaluator = get_evaluator()

    with session_scope() as session:
        jobs = session.query(Job).filter(Job.is_active.is_(True)).all()
        spent_today = 0.0

        for job in jobs:
            already = session.query(JobAnalysisRecord).filter_by(job_id=job.id, profile_version="v1").first()
            if already is not None:
                continue

            from jobintel.geography.classifier import classify_geography
            geo = classify_geography(job.location_raw, job.job_description_clean)

            analysis, role_match, mismatches = score_career_opportunity(
                job_title=job.job_title,
                description_text=job.job_description_clean,
                geo_evidence=geo,
                published_at=job.published_at,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                is_strategic_company=job.company_name.strip().lower() in strategic_names,
                full_description_available=bool(job.job_description_clean),
                source_is_aggregator_only=_is_aggregator_only(job),
            )

            # Two independent gates before spending money on an LLM call
            # (spec §45): the deterministic score has to be high enough to
            # be worth refining, AND the vacancy has to be topically close
            # to the CV corpus at all. A high-scoring posting that is
            # semantically unrelated is exactly the case where a paid call
            # buys nothing.
            prescore = semantic_prescore(job.job_title, job.job_description_clean)
            if (
                analysis.overall_score >= stage4_threshold
                and prescore >= stage2_threshold
                and spent_today < daily_budget
            ):
                evidence_texts = get_evidence_for_categories(role_match.evidence_categories) if role_match.role_family else []
                refinement, usage = await evaluator.evaluate(
                    job_title=job.job_title,
                    description_text=job.job_description_clean,
                    cv_evidence_texts=evidence_texts,
                    deterministic_analysis=analysis,
                )
                if usage is not None:
                    session.add(LlmUsage(
                        job_id=job.id, provider=usage.provider, model=usage.model,
                        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                        cost_usd=usage.cost_usd, stage="stage3",
                    ))
                    spent_today += usage.cost_usd
                    summary.total_llm_cost_usd += usage.cost_usd
                if refinement is not None:
                    analysis = apply_refinement(analysis, refinement)
                    summary.llm_evaluated += 1

            record = JobAnalysisRecord(
                job_id=job.id, profile_version=analysis.profile_version,
                remote_score=analysis.remote_score, experience_score=analysis.experience_score,
                skills_score=analysis.skills_score, training_advantage_score=analysis.training_advantage_score,
                ai_cyber_intersection_score=analysis.ai_cyber_intersection_score,
                interview_probability_score=analysis.interview_probability_score,
                compensation_score=analysis.compensation_score, freshness_score=analysis.freshness_score,
                strategic_company_bonus=analysis.strategic_company_bonus,
                can_do_score=analysis.can_do_score, desirability_score=analysis.desirability_score,
                overall_score=analysis.overall_score, confidence_score=analysis.confidence_score,
                recommendation=analysis.recommendation.value,
                mandatory_mismatches=analysis.mandatory_mismatches, preferred_gaps=analysis.preferred_gaps,
                strengths=analysis.strengths, concerns=analysis.concerns,
                geographic_evidence=analysis.geographic_evidence, reasoning_summary=analysis.reasoning_summary,
                application_readiness=analysis.application_readiness,
                model_used=analysis.model_used, prompt_version=analysis.prompt_version,
            )
            session.add(record)
            job.role_family = role_match.role_family

            summary.evaluated += 1
            if analysis.recommendation.value == "INELIGIBLE":
                summary.ineligible += 1
            elif analysis.recommendation.value == "STRONG_APPLY":
                summary.strong_matches += 1
            elif analysis.recommendation.value == "EXCEPTIONAL_MATCH":
                summary.exceptional_matches += 1

        _evaluate_gigs(session, summary, min_quality_score=_minimum_digest_score())

    return summary


def _minimum_digest_score() -> float:
    from jobintel.settings import load_profile

    return float(load_profile().get("scoring", {}).get("minimum_digest_score", 75))
