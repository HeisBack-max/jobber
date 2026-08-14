from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jobintel.geography.classifier import classify_geography
from jobintel.matching.career_scorer import score_career_opportunity
from jobintel.matching.gig_scorer import score_gig
from jobintel.matching.negative_matcher import find_mismatches
from jobintel.matching.role_matcher import match_role_family
from jobintel.models.enums import Recommendation
from tests import fixtures as fx


def test_ai_trainer_matches_tier_a_role_family():
    result = match_role_family("Generative AI Trainer", fx.PERFECT_WORLDWIDE_AI_TRAINER[1])
    assert result.role_family == "ai_training"
    assert result.tier == "A"


def test_generic_enablement_title_does_not_false_match_ai_training():
    """Regression test: a business role that merely shares the word
    "enablement" with "AI Enablement Specialist" (e.g. GTM/sales/partner
    enablement at an AI company, where the company boilerplate mentions
    "AI" regardless of the role) must not be scored as a Tier-A AI
    training match (spec §51 false-positive protection)."""
    desc = (
        "ABOUT ACME AI\nAcme AI is an AI research and product company. "
        "We launched in 2023 with the first human-like AI voice model. "
        "This role drives GTM enablement for our expansion sales teams, "
        "building playbooks and onboarding new account executives."
    )
    result = match_role_family("GTM Enablement - Expansion", desc)
    assert result.role_family != "ai_training"


def test_ai_security_title_still_matches_despite_stricter_gate():
    result = match_role_family(
        "AI Security Enablement Lead",
        "Lead LLM red-teaming and adversarial testing for enterprise AI security.",
    )
    assert result.role_family == "ai_security"
    assert result.tier == "A"


def test_unrelated_engineer_title_does_not_false_match_prompt_engineering():
    """Regression test: sharing only the word "Engineer" with "Prompt
    Engineer" produced a deceptively high fuzzy title ratio (0.84) for a
    completely unrelated facilities role - the anchor gate must require
    the real anchor term in the title, not accept a high fuzzy ratio as
    a substitute (spec §51)."""
    result = match_role_family(
        "AV Engineer", "Install and maintain audio-visual equipment in conference rooms."
    )
    assert result.role_family is None


def test_tax_role_does_not_match_any_family():
    """Regression test: token_set_ratio's character-level fuzzy component
    can score moderately even between titles with zero shared words
    (observed 0.51 for "International Indirect Tax, VAT/GST" vs.
    "Technical Instructional Designer"). The title floor must reject it."""
    result = match_role_family(
        "International Indirect Tax, VAT/GST",
        "About Acme AI. Acme's mission is to build safe AI systems. "
        "Manage indirect tax compliance across multiple jurisdictions.",
    )
    assert result.role_family is None


def test_irrelevant_software_engineer_flagged_mandatory_mismatch():
    mismatches = find_mismatches(fx.IRRELEVANT_SOFTWARE_ENGINEER[1])
    assert mismatches.mandatory_mismatches, "expected an unsupported-experience mismatch to be detected"


def test_perfect_worldwide_ai_trainer_scores_strong_apply_or_better():
    title = "Generative AI Trainer"
    loc, desc = fx.PERFECT_WORLDWIDE_AI_TRAINER
    geo = classify_geography(loc, desc)
    analysis, role_match, mismatches = score_career_opportunity(
        job_title=title,
        description_text=desc,
        geo_evidence=geo,
        published_at=datetime.now(UTC) - timedelta(hours=5),
        salary_min=None,
        salary_max=None,
        is_strategic_company=False,
        full_description_available=True,
        source_is_aggregator_only=False,
    )
    assert analysis.overall_score >= 60
    assert analysis.recommendation in (
        Recommendation.EXCEPTIONAL_MATCH, Recommendation.STRONG_APPLY, Recommendation.WORTH_REVIEWING,
    )
    assert not mismatches.mandatory_mismatches


def test_us_only_role_is_ineligible_regardless_of_fit():
    title = "Cybersecurity Trainer"
    loc, desc = fx.US_ONLY_REMOTE_CYBERSECURITY_TRAINER
    geo = classify_geography(loc, desc)
    analysis, _, _ = score_career_opportunity(
        job_title=title,
        description_text=desc,
        geo_evidence=geo,
        published_at=datetime.now(UTC),
        salary_min=None,
        salary_max=None,
        is_strategic_company=False,
        full_description_available=True,
        source_is_aggregator_only=False,
    )
    assert analysis.recommendation == Recommendation.INELIGIBLE


def test_irrelevant_software_engineer_capped_low_despite_worldwide_remote():
    title = "Senior Backend Software Engineer"
    loc, desc = fx.IRRELEVANT_SOFTWARE_ENGINEER
    geo = classify_geography(loc, desc)
    analysis, _, mismatches = score_career_opportunity(
        job_title=title,
        description_text=desc,
        geo_evidence=geo,
        published_at=datetime.now(UTC),
        salary_min=None,
        salary_max=None,
        is_strategic_company=False,
        full_description_available=True,
        source_is_aggregator_only=False,
    )
    assert mismatches.mandatory_mismatches
    assert analysis.overall_score <= 55
    assert analysis.recommendation in (Recommendation.LOW_PRIORITY, Recommendation.IGNORE, Recommendation.STRETCH_OPPORTUNITY)


def test_regular_us_travel_excludes_otherwise_good_role():
    loc, desc = fx.REGULAR_US_TRAVEL_REQUIRED
    geo = classify_geography(loc, desc)
    analysis, _, _ = score_career_opportunity(
        job_title="AI Enablement Specialist",
        description_text=desc,
        geo_evidence=geo,
        published_at=datetime.now(UTC),
        salary_min=None,
        salary_max=None,
        is_strategic_company=False,
        full_description_available=True,
        source_is_aggregator_only=False,
    )
    assert analysis.recommendation == Recommendation.EXCLUDED_TRAVEL_REQUIREMENT


def test_low_paid_annotation_gig_scores_low():
    loc, desc = fx.LOW_PAID_GENERIC_ANNOTATION_GIG
    geo = classify_geography(loc, desc)
    result = score_gig(
        title="Data Annotation Contributor",
        description_text=desc,
        geo_evidence=geo,
        hourly_rate_min=3,
        hourly_rate_max=5,
        weekly_hours_min=10,
        weekly_hours_max=20,
        platform_reliability=0.6,
    )
    assert result.is_commodity_annotation
    assert result.gig_quality_score <= 35


def test_high_value_specialist_gig_scores_well():
    loc, desc = fx.HIGH_VALUE_SPECIALIST_AI_EVALUATION_GIG
    geo = classify_geography(loc, desc)
    result = score_gig(
        title="LLM Security Evaluation Specialist",
        description_text=desc,
        geo_evidence=geo,
        hourly_rate_min=65,
        hourly_rate_max=90,
        weekly_hours_min=10,
        weekly_hours_max=20,
        platform_reliability=0.8,
    )
    assert not result.is_commodity_annotation
    assert result.gig_quality_score >= 60
