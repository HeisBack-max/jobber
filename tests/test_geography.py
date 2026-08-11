"""Geography/eligibility engine tests - the highest-risk correctness code
in the system per ARCHITECTURE.md §7. Every scenario asserts the actual
classification/eligibility decision, not just that the code runs."""

from __future__ import annotations

from jobintel.geography.classifier import classify_geography
from jobintel.geography.eligibility import excluded_travel_override, finalize_eligibility
from jobintel.models.enums import EligibilityStatus, RemoteClassification
from tests import fixtures as fx


def test_perfect_worldwide_ai_trainer():
    ev = classify_geography(*fx.PERFECT_WORLDWIDE_AI_TRAINER)
    assert ev.classification == RemoteClassification.REMOTE_WORLDWIDE
    assert ev.eligible == EligibilityStatus.YES
    assert ev.confidence >= 0.8


def test_us_only_remote_excluded():
    ev = classify_geography(*fx.US_ONLY_REMOTE_CYBERSECURITY_TRAINER)
    assert ev.classification == RemoteClassification.REMOTE_US_ONLY
    assert ev.eligible == EligibilityStatus.NO
    assert ev.us_presence_required is True


def test_thailand_only_remote_excluded():
    ev = classify_geography(*fx.THAILAND_RESIDENT_ONLY_AI_ROLE)
    assert ev.classification == RemoteClassification.REMOTE_THAILAND_ONLY
    assert ev.eligible == EligibilityStatus.NO
    assert ev.thailand_presence_required is True


def test_us_company_worldwide_remote_is_accepted():
    """Company nationality must never determine eligibility (spec §3)."""
    ev = classify_geography(*fx.US_STARTUP_HIRING_WORLDWIDE)
    assert ev.classification == RemoteClassification.REMOTE_WORLDWIDE
    assert ev.eligible == EligibilityStatus.YES


def test_thai_company_worldwide_remote_is_accepted():
    ev = classify_geography(*fx.THAI_STARTUP_HIRING_WORLDWIDE)
    assert ev.classification == RemoteClassification.REMOTE_WORLDWIDE
    assert ev.eligible == EligibilityStatus.YES


def test_hybrid_london_role_eligible_but_not_worldwide():
    ev = classify_geography(*fx.HYBRID_AI_ROLE_LONDON)
    assert ev.classification == RemoteClassification.HYBRID
    assert ev.eligible == EligibilityStatus.YES
    assert ev.office_country == "United Kingdom"


def test_misleading_remote_us_advertisement_is_excluded():
    """A vacancy that says "Remote" but is scoped to the US must not be
    treated as worldwide remote (spec §12/§13)."""
    ev = classify_geography(*fx.MISLEADING_REMOTE_ADVERTISEMENT)
    assert ev.classification == RemoteClassification.REMOTE_US_ONLY
    assert ev.eligible == EligibilityStatus.NO


def test_anthropic_style_remote_friendly_travel_required_is_not_auto_passed():
    """"Remote-Friendly (Travel-Required)" alone is insufficient evidence
    of geographic eligibility (spec §17) - must not resolve to YES."""
    ev = classify_geography(*fx.ANTHROPIC_STYLE_REMOTE_FRIENDLY_TRAVEL_REQUIRED)
    assert ev.eligible != EligibilityStatus.YES
    assert ev.classification != RemoteClassification.REMOTE_WORLDWIDE


def test_openai_london_office_role_eligible_but_onsite():
    """Geographically eligible (UK is not excluded) but poor remote
    suitability - onsite/hybrid, never silently promoted to remote."""
    ev = classify_geography(*fx.OPENAI_LONDON_OPPORTUNITY)
    assert ev.classification == RemoteClassification.ONSITE
    assert ev.eligible == EligibilityStatus.YES
    assert ev.office_country == "United Kingdom"


def test_strong_ai_security_opportunity_is_emea_eligible():
    ev = classify_geography(*fx.STRONG_AI_SECURITY_OPPORTUNITY)
    assert ev.classification == RemoteClassification.REMOTE_EMEA
    assert ev.eligible == EligibilityStatus.YES


def test_remote_university_instructor_worldwide():
    ev = classify_geography(*fx.REMOTE_UNIVERSITY_CYBERSECURITY_INSTRUCTOR)
    assert ev.classification == RemoteClassification.REMOTE_WORLDWIDE
    assert ev.eligible == EligibilityStatus.YES


def test_vertex_ai_consultant_role_uk_emea_eligible():
    ev = classify_geography(*fx.STRONG_VERTEX_AI_CONSULTANT_ROLE)
    assert ev.eligible == EligibilityStatus.YES


def test_regular_us_travel_flagged_for_override():
    ev = classify_geography(*fx.REGULAR_US_TRAVEL_REQUIRED)
    assert ev.travel_required is True
    assert "United States" in ev.travel_destinations
    assert excluded_travel_override(ev) is True


def test_regular_thailand_travel_flagged_for_override():
    ev = classify_geography(*fx.REGULAR_THAILAND_TRAVEL_REQUIRED)
    assert ev.travel_required is True
    assert "Thailand" in ev.travel_destinations
    assert excluded_travel_override(ev) is True


def test_occasional_international_travel_not_excluded():
    """Occasional exceptional travel does not disqualify an opportunity
    (spec §3)."""
    ev = classify_geography(*fx.OCCASIONAL_INTERNATIONAL_TRAVEL)
    assert excluded_travel_override(ev) is False
    assert ev.eligible == EligibilityStatus.YES


def test_ambiguous_country_only_role_routes_to_unclear():
    ev = classify_geography("Remote", "We are a remote-first company.")
    assert ev.eligible == EligibilityStatus.UNCLEAR


def test_finalize_eligibility_downgrades_unspecified_excluded_travel():
    ev = classify_geography(
        "Remote - Worldwide",
        "Remote worldwide role. Some travel to the United States may be required.",
    )
    # No frequency given -> ambiguous -> should not remain a clean YES.
    assert finalize_eligibility(ev) == EligibilityStatus.UNCLEAR


def test_gig_worldwide_eligible():
    ev = classify_geography(*fx.HIGH_VALUE_SPECIALIST_AI_EVALUATION_GIG)
    assert ev.eligible == EligibilityStatus.YES


def test_low_paid_gig_still_geographically_worldwide():
    """Geography classification is independent of compensation quality -
    downranking commodity gigs happens in scoring, not geography."""
    ev = classify_geography(*fx.LOW_PAID_GENERIC_ANNOTATION_GIG)
    assert ev.classification == RemoteClassification.REMOTE_WORLDWIDE
    assert ev.eligible == EligibilityStatus.YES
