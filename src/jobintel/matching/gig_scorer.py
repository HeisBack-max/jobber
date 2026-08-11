"""Gig/project scoring (spec §21) - a separate model from career scoring.
A high-quality short gig must never be penalized merely for being short."""

from __future__ import annotations

from dataclasses import dataclass

from jobintel.geography.eligibility import finalize_eligibility
from jobintel.matching.role_matcher import match_role_family
from jobintel.models.enums import EligibilityStatus
from jobintel.models.schemas import GeographicEvidence
from jobintel.settings import load_scoring

_LOW_VALUE_TERMS = {"data annotation", "data labeling", "data labelling", "image tagging"}
_SPECIALIST_TERMS = {
    "red team", "red-team", "adversarial", "jailbreak", "security evaluation",
    "llm evaluation", "ai safety", "prompt injection", "cybersecurity",
}


@dataclass
class GigScoreResult:
    gig_quality_score: float
    geographic_compatibility: float
    professional_relevance: float
    compensation: float
    flexibility: float
    ai_cyber_career_value: float
    source_reliability: float
    time_commitment_compatibility: float
    is_commodity_annotation: bool


def score_gig(
    title: str,
    description_text: str,
    geo_evidence: GeographicEvidence,
    hourly_rate_min: float | None,
    hourly_rate_max: float | None,
    weekly_hours_min: float | None,
    weekly_hours_max: float | None,
    platform_reliability: float,  # 0-1, curated per platform
) -> GigScoreResult:
    weights = load_scoring()["gig_scoring"]["weights"]
    text_lower = (description_text or "").lower()

    eligible = finalize_eligibility(geo_evidence)
    geo_compat = weights["geographic_compatibility"] if eligible == EligibilityStatus.YES else (
        weights["geographic_compatibility"] * 0.4 if eligible == EligibilityStatus.UNCLEAR else 0.0
    )

    role_match = match_role_family(title, description_text)
    is_commodity = any(term in text_lower for term in _LOW_VALUE_TERMS)
    is_specialist = any(term in text_lower for term in _SPECIALIST_TERMS)
    if is_commodity and not is_specialist:
        professional_relevance = weights["professional_relevance"] * 0.1
    else:
        professional_relevance = role_match.combined_score * weights["professional_relevance"]

    rate = hourly_rate_max or hourly_rate_min
    if rate is None:
        compensation = weights["compensation"] * 0.5  # UNKNOWN -> neutral
    elif rate >= 50:
        compensation = weights["compensation"]
    elif rate >= 25:
        compensation = weights["compensation"] * 0.7
    elif rate >= 12:
        compensation = weights["compensation"] * 0.4
    else:
        compensation = weights["compensation"] * 0.15

    if weekly_hours_max is not None and weekly_hours_max <= 20:
        flexibility = weights["flexibility"]
    elif weekly_hours_max is not None and weekly_hours_max <= 35:
        flexibility = weights["flexibility"] * 0.7
    else:
        flexibility = weights["flexibility"] * 0.5

    ai_cyber_value = weights["ai_cyber_career_value"] if is_specialist else (
        weights["ai_cyber_career_value"] * 0.5 if role_match.role_family else 0.0
    )

    source_reliability = weights["source_reliability"] * max(0.0, min(1.0, platform_reliability))

    time_commitment = weights["time_commitment_compatibility"]  # gigs are inherently flexible by class

    total = (
        geo_compat + professional_relevance + compensation + flexibility
        + ai_cyber_value + source_reliability + time_commitment
    )
    total = max(0.0, min(100.0, total))
    if is_commodity and not is_specialist:
        total = min(total, 35.0)  # never rank commodity annotation highly (spec §20)

    return GigScoreResult(
        gig_quality_score=total,
        geographic_compatibility=geo_compat,
        professional_relevance=professional_relevance,
        compensation=compensation,
        flexibility=flexibility,
        ai_cyber_career_value=ai_cyber_value,
        source_reliability=source_reliability,
        time_commitment_compatibility=time_commitment,
        is_commodity_annotation=is_commodity and not is_specialist,
    )
