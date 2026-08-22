"""CV tailoring and cover-letter drafting, grounded in the CV evidence map."""

from jobintel.tailoring.generator import (
    CoverLetterDraft,
    TailoringBrief,
    build_cover_letter,
    build_tailoring_brief,
)
from jobintel.tailoring.guardrails import ClaimViolation, validate_generated_text

__all__ = [
    "ClaimViolation",
    "CoverLetterDraft",
    "TailoringBrief",
    "build_cover_letter",
    "build_tailoring_brief",
    "validate_generated_text",
]
