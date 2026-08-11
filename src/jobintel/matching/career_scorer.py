"""Deterministic, fully explainable career-opportunity scoring (spec §22-27).

This is also what powers Stage 2 semantic pre-scoring (spec §45) and is
the score used verbatim (model_used="deterministic") whenever no LLM
evaluator is configured - the app never fabricates a plausible-looking
LLM score it didn't actually compute.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from jobintel.geography.eligibility import excluded_travel_override, finalize_eligibility
from jobintel.matching.cv_evidence import get_evidence_for_categories
from jobintel.matching.negative_matcher import MismatchResult, find_mismatches
from jobintel.matching.role_matcher import RoleMatchResult, match_role_family
from jobintel.models.enums import ApplicationReadiness, EligibilityStatus, Recommendation
from jobintel.models.schemas import GeographicEvidence, JobAnalysis
from jobintel.settings import load_scoring

_TRAINING_FAMILIES = {
    "ai_training", "cybersecurity_training", "technical_training",
    "technical_instructional_design", "university_academic", "customer_education",
}
_AI_CYBER_FAMILIES = {
    "ai_security", "ai_evaluation", "cybersecurity_training",
    "prompt_engineering", "cybersecurity_consulting",
}
_AI_TERMS = re.compile(
    r"\bai\b|artificial intelligence|generative ai|\bllm\b|large language model", re.I
)
_CYBER_TERMS = re.compile(
    r"cybersecurity|cyber security|penetration testing|osint|red[\s-]team|grc\b", re.I
)


def _freshness_score(published_at: datetime | None, now: datetime, bands: list[dict]) -> tuple[float, bool]:
    if published_at is None:
        return 0.0, True
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_days = (now - published_at).total_seconds() / 86400
    for band in bands:
        max_age = band["max_age_days"]
        if max_age is None or age_days <= max_age:
            return float(band["score"]), False
    return 0.0, False


def _compensation_score(salary_min: float | None, salary_max: float | None) -> tuple[float, bool]:
    if salary_min is None and salary_max is None:
        return 2.5, True  # UNKNOWN -> neutral, never zero (spec §48)
    value = salary_max or salary_min or 0
    # Heuristic banding in GBP-equivalent annualized terms; deliberately
    # coarse since currency/period normalization confidence varies.
    if value >= 70000:
        return 5.0, False
    if value >= 45000:
        return 3.5, False
    if value >= 25000:
        return 2.0, False
    return 1.0, False


def score_career_opportunity(
    job_title: str,
    description_text: str,
    geo_evidence: GeographicEvidence,
    published_at: datetime | None,
    salary_min: float | None,
    salary_max: float | None,
    is_strategic_company: bool,
    full_description_available: bool,
    source_is_aggregator_only: bool,
    now: datetime | None = None,
) -> tuple[JobAnalysis, RoleMatchResult, MismatchResult]:
    now = now or datetime.now(UTC)
    scoring = load_scoring()
    weights = scoring["career_scoring"]["weights"]
    remote_scale = scoring["remote_scoring_scale"]
    freshness_bands = scoring["freshness_scoring"]["bands"]
    rec_bands = scoring["recommendation_thresholds"]["bands"]
    conf = scoring["confidence_scoring"]

    role_match = match_role_family(job_title, description_text)
    mismatches = find_mismatches(description_text)

    final_eligible = finalize_eligibility(geo_evidence)
    is_excluded_travel = excluded_travel_override(geo_evidence)

    # --- component scores, each already scaled to its weight's max ---
    remote_score = float(remote_scale.get(geo_evidence.classification.value, remote_scale.get("UNCLEAR", 9)))
    remote_score = min(remote_score, weights["remote_suitability"])

    experience_score = role_match.combined_score * weights["experience_relevance"]

    evidence_texts = get_evidence_for_categories(role_match.evidence_categories) if role_match.role_family else []
    skills_score = (min(1.0, role_match.keyword_score + (0.2 if evidence_texts else 0.0))) * weights["skills_alignment"]

    training_advantage = (
        weights["training_communication_advantage"]
        if role_match.role_family in _TRAINING_FAMILIES
        else weights["training_communication_advantage"] * 0.5
        if role_match.role_family
        else weights["training_communication_advantage"] * 0.2
    )

    has_ai = bool(_AI_TERMS.search(description_text or ""))
    has_cyber = bool(_CYBER_TERMS.search(description_text or ""))
    if role_match.role_family in _AI_CYBER_FAMILIES or (has_ai and has_cyber):
        ai_cyber_score = weights["ai_cyber_intersection"]
    elif has_ai or has_cyber:
        ai_cyber_score = weights["ai_cyber_intersection"] * 0.5
    else:
        ai_cyber_score = 0.0

    compensation_score, salary_unreliable = _compensation_score(salary_min, salary_max)
    compensation_score = min(compensation_score, weights["compensation"])

    freshness_score, no_pub_date = _freshness_score(published_at, now, freshness_bands)

    strategic_bonus = min(3.0, scoring["career_scoring"]["strategic_company_bonus_max"]) if is_strategic_company else 0.0

    interview_component_max = weights["interview_plausibility"]
    mismatch_penalty = min(interview_component_max, len(mismatches.mandatory_mismatches) * (interview_component_max / 2))
    interview_component = max(0.0, interview_component_max - mismatch_penalty) if not mismatches.mandatory_mismatches else 0.0
    if not mismatches.mandatory_mismatches:
        interview_component = interview_component_max * (0.5 + 0.5 * role_match.combined_score)

    overall_score = (
        remote_score + experience_score + interview_component + skills_score
        + training_advantage + ai_cyber_score + compensation_score + freshness_score
        + strategic_bonus
    )
    overall_score = max(0.0, min(100.0, overall_score))
    if mismatches.mandatory_mismatches:
        overall_score = min(overall_score, 55.0)  # fatal mismatch caps the score hard

    can_do_score = min(100.0, ((experience_score + skills_score + training_advantage + ai_cyber_score)
                                / max(1.0, weights["experience_relevance"] + weights["skills_alignment"]
                                      + weights["training_communication_advantage"] + weights["ai_cyber_intersection"])) * 100)
    desirability_max = weights["remote_suitability"] + weights["compensation"] + weights["freshness"]
    desirability_score = min(100.0, ((remote_score + compensation_score + freshness_score) / max(1.0, desirability_max)) * 100)
    interview_probability_overall = min(100.0, (interview_component / max(1.0, interview_component_max)) * 100)
    if mismatches.mandatory_mismatches:
        interview_probability_overall = min(interview_probability_overall, 20.0)

    # --- confidence ---
    confidence = float(conf["base"])
    if not full_description_available:
        confidence -= conf["deductions"]["full_description_unavailable"]
    if geo_evidence.confidence < 0.5:
        confidence -= conf["deductions"]["remote_rules_unclear"]
    if final_eligible == EligibilityStatus.UNCLEAR:
        confidence -= conf["deductions"]["geography_ambiguous"]
    if no_pub_date:
        confidence -= conf["deductions"]["publication_date_unavailable"]
    if salary_unreliable:
        confidence -= conf["deductions"]["salary_data_unreliable"]
    if source_is_aggregator_only:
        confidence -= conf["deductions"]["aggregator_only_source"]
    confidence = max(float(conf["floor"]), confidence)

    # --- recommendation ---
    if final_eligible == EligibilityStatus.NO:
        recommendation = Recommendation.INELIGIBLE
    elif is_excluded_travel:
        recommendation = Recommendation.EXCLUDED_TRAVEL_REQUIREMENT
    else:
        recommendation = Recommendation.IGNORE
        for band in rec_bands:
            if overall_score >= band["min_score"]:
                recommendation = Recommendation(band["label"])
                break

    strengths = []
    if role_match.role_family:
        strengths.append(f"Role-family match: {role_match.label} ({role_match.tier} priority).")
    strengths.extend(evidence_texts)
    if remote_score >= 18:
        strengths.append(f"Strong remote suitability ({geo_evidence.classification.value}).")

    concerns = list(mismatches.preferred_gaps)
    if geo_evidence.confidence < 0.6:
        concerns.append("Geographic eligibility language was not fully unambiguous - verify before applying.")
    if salary_unreliable:
        concerns.append("Compensation not stated (UNKNOWN) - scored neutrally.")

    if mismatches.mandatory_mismatches:
        readiness = ApplicationReadiness.NOT_RECOMMENDED
    elif overall_score >= 85 and not mismatches.preferred_gaps:
        readiness = ApplicationReadiness.READY
    elif overall_score >= 75:
        readiness = ApplicationReadiness.READY_WITH_MINOR_CV_TAILORING
    elif overall_score >= 60:
        readiness = ApplicationReadiness.NEEDS_TARGETED_COVER_LETTER
    else:
        readiness = ApplicationReadiness.NEEDS_MAJOR_REPOSITIONING

    reasoning_parts = []
    if role_match.role_family:
        reasoning_parts.append(f"Matched role family '{role_match.label}'.")
    reasoning_parts.append(f"Geographic eligibility: {final_eligible.value} ({geo_evidence.classification.value}).")
    if mismatches.mandatory_mismatches:
        reasoning_parts.append(f"{len(mismatches.mandatory_mismatches)} mandatory mismatch(es) found.")
    reasoning_parts.append(f"Overall score {overall_score:.1f}/100 -> {recommendation.value}.")

    analysis = JobAnalysis(
        profile_version="v1",
        remote_score=remote_score,
        experience_score=experience_score,
        skills_score=skills_score,
        training_advantage_score=training_advantage,
        ai_cyber_intersection_score=ai_cyber_score,
        interview_probability_score=interview_component,
        compensation_score=compensation_score,
        freshness_score=freshness_score,
        strategic_company_bonus=strategic_bonus,
        can_do_score=can_do_score,
        interview_probability_score_overall=interview_probability_overall,
        desirability_score=desirability_score,
        overall_score=overall_score,
        confidence_score=confidence,
        recommendation=recommendation,
        mandatory_mismatches=mismatches.mandatory_mismatches,
        preferred_gaps=mismatches.preferred_gaps,
        strengths=strengths,
        concerns=concerns,
        geographic_evidence=geo_evidence.evidence,
        reasoning_summary=" ".join(reasoning_parts),
        application_readiness=readiness.value,
        model_used="deterministic",
        prompt_version="v1",
    )
    return analysis, role_match, mismatches
