"""Combines raw GeographicEvidence with profile travel rules to decide
the final EXCLUDED_TRAVEL_REQUIREMENT override (spec §3, §23).

Kept separate from the classifier so the classifier stays a pure text ->
evidence function, independently testable, while this module encodes the
policy decision (which countries are excluded, what counts as "regular").
"""

from __future__ import annotations

from jobintel.geography.country_data import REGULAR_TRAVEL_FREQUENCY_TERMS
from jobintel.models.enums import EligibilityStatus
from jobintel.models.schemas import GeographicEvidence

DEFAULT_EXCLUDED_TRAVEL_COUNTRIES = {"United States", "Thailand"}


def excluded_travel_override(
    evidence: GeographicEvidence,
    excluded_countries: set[str] = frozenset(DEFAULT_EXCLUDED_TRAVEL_COUNTRIES),
) -> bool:
    """True when travel to an excluded country is described as regular/material.

    Ambiguous (frequency unspecified) travel to an excluded country does
    NOT trigger the hard override - it is surfaced as reduced confidence /
    manual review instead, so an isolated "some travel may be required"
    sentence doesn't wrongly kill an otherwise excellent opportunity.
    """
    if not evidence.travel_required or not evidence.travel_destinations:
        return False
    if not any(d in excluded_countries for d in evidence.travel_destinations):
        return False
    return evidence.travel_frequency in REGULAR_TRAVEL_FREQUENCY_TERMS


def finalize_eligibility(
    evidence: GeographicEvidence,
    excluded_countries: set[str] = frozenset(DEFAULT_EXCLUDED_TRAVEL_COUNTRIES),
) -> EligibilityStatus:
    """Downgrades an otherwise-YES eligibility to UNCLEAR when travel to an
    excluded country is mentioned with no frequency information, so it
    routes to manual review instead of silently passing."""
    if (
        evidence.eligible == EligibilityStatus.YES
        and evidence.travel_destinations
        and any(d in excluded_countries for d in evidence.travel_destinations)
        and evidence.travel_frequency is None
    ):
        return EligibilityStatus.UNCLEAR
    return evidence.eligible
