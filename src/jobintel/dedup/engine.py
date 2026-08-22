"""Deduplication and source-provenance rules (spec §35/§36/§52).

Kept as pure functions over NormalizedJob so dedup logic is testable
without a database. The pipeline layer (jobintel.pipeline) is the only
place that touches SQLAlchemy sessions.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from jobintel.models.schemas import NormalizedJob

# Lower rank = higher quality/more authoritative source (spec §52).
SOURCE_QUALITY_RANK = {
    "official_employer": 1,
    "official_ats": 1,
    # A gig Richard pasted in himself from a platform this app cannot
    # collect: first-hand, so better than an aggregator's copy, but it
    # must not overwrite an employer's own ATS text.
    "manual_entry": 2,
    "board": 3,
    "aggregator": 4,
    "unknown": 5,
}

TITLE_FUZZY_MATCH_THRESHOLD = 88


def _normalize_company(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _normalize_location(location: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (location or "").lower())


def is_duplicate(a: NormalizedJob, b: NormalizedJob) -> bool:
    """True when `a` and `b` are almost certainly the same underlying
    vacancy, discovered through the same or a different source."""
    if a.source == b.source and a.source_job_id == b.source_job_id:
        return True
    if a.content_hash and a.content_hash == b.content_hash:
        return True
    if _normalize_company(a.company_name) != _normalize_company(b.company_name):
        return False
    title_ratio = fuzz.token_set_ratio(a.normalized_job_title.lower(), b.normalized_job_title.lower())
    if title_ratio < TITLE_FUZZY_MATCH_THRESHOLD:
        return False
    loc_a, loc_b = _normalize_location(a.location_raw), _normalize_location(b.location_raw)
    if loc_a and loc_b and loc_a != loc_b:
        return False
    return True


def should_overwrite(existing_source_type: str, new_source_type: str) -> bool:
    """A lower-quality source must never overwrite better official data
    (spec §35/§52) - only overwrite when the new source is at least as
    authoritative as what's already stored."""
    existing_rank = SOURCE_QUALITY_RANK.get(existing_source_type, SOURCE_QUALITY_RANK["unknown"])
    new_rank = SOURCE_QUALITY_RANK.get(new_source_type, SOURCE_QUALITY_RANK["unknown"])
    return new_rank <= existing_rank


def classify_change(existing_seen_before: bool, existing_content_hash: str | None, new_content_hash: str) -> str:
    """Distinguishes new / updated / duplicate for a job already matched
    by is_duplicate() (spec §36)."""
    if not existing_seen_before:
        return "new"
    if existing_content_hash == new_content_hash:
        return "duplicate"
    return "updated"
