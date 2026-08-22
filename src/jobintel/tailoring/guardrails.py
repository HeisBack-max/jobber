"""Anti-fabrication guardrails for generated application material
(spec §27/§28/§39).

An application document is the one artefact this system produces that
Richard might send to an employer under his own name. A hallucinated
claim there is not a ranking error - it is a lie in a job application.
So every generated text, whether it came from a deterministic template
or from an LLM, is validated against the same rules before it is stored
or shown:

1. Nothing may claim experience in a domain listed under
   `explicit_non_evidence.unsupported_domains` in the CV evidence map.
2. The MSc Data Analytics must never be described as completed - the CV
   says "in progress, expected 2027" (IMPLEMENTATION_PLAN.md §1).
3. No language other than English may be claimed, since the CV evidences
   none, despite extensive work in non-English-speaking countries.
4. Nothing may claim US citizenship, US work authorization, or a
   security clearance.

Validation is fail-closed for LLM output: a draft that trips any rule is
discarded and the deterministic draft is used instead. It is better to
send a plainer letter than a false one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jobintel.matching.negative_matcher import LANGUAGES_NOT_EVIDENCED
from jobintel.settings import load_cv_evidence_map

# Verbs and possessives that turn a mention into a claim. Kept as one
# list because the earlier per-rule spellings diverged and let the most
# natural phrasing through: "I have an MSc in Data Analytics" was not
# caught, because the list had `completed|holds|earned|my` but not
# `have`. Anything that asserts possession belongs here.
_CLAIM_VERBS = (
    # Deliberately no bare "a/an": "the role calls for a completed
    # master's degree" is a statement about the *posting*, not a claim
    # about the candidate, and blocking it would stop the letter from
    # naming the gap honestly. Possession is what makes it a claim.
    r"(?:completed|complete|holds?|holding|held|have|has|having|earned|obtained|received|"
    r"awarded|finished|gained|achieved|possess(?:es)?|my|with an?)"
)


@dataclass(frozen=True)
class ClaimViolation:
    rule: str
    detail: str
    matched_text: str


# Each rule is (name, pattern, explanation, context_exemption). Patterns
# catch the *assertive* phrasing a generated document would use, not
# every mention of the topic: a cover letter may legitimately say "I am
# studying towards an MSc", and must not say "my MSc in Data Analytics".
# `context_exemption` is checked in a window around the match, because
# the words that make a mention honest ("studying towards", "in
# progress") can appear on either side of it.
CONTEXT_WINDOW_CHARS = 60

_RULES: list[tuple[str, re.Pattern, str, re.Pattern | None]] = [
    (
        "msc_must_be_in_progress",
        re.compile(
            rf"\b{_CLAIM_VERBS}\s+(?:[\w\s,'-]{{0,30}}\s)?(?:msc|m\.sc\.?|master'?s)\b"
            r"|\b(?:msc|master'?s)\s+(?:degree\s+)?(?:graduate|holder|qualified)\b"
            r"|\bgraduated\s+(?:with\s+)?(?:an?\s+)?(?:msc|master'?s)\b",
            re.I,
        ),
        "The MSc Data Analytics is in progress (expected 2027) and must never be presented as completed or held.",
        re.compile(
            # Honest framings that must not be blocked: the qualification
            # described as in progress, or a requirement named as a gap.
            r"\b(?:in progress|in-progress|ongoing|expected|studying|towards|due to complete|"
            r"not yet completed|not part of my background|do not hold|have not completed|"
            r"outside my background)\b",
            re.I,
        ),
    ),
    (
        "no_unevidenced_languages",
        re.compile(
            # One shared language list with the negative matcher: the two
            # had drifted, and the shorter list here let a cover letter
            # claim fluent Dutch, Polish, Croatian, Swedish or Ukrainian.
            rf"\b(?:fluent|fluency|proficient|proficiency|native|conversational|bilingual|speaks?|"
            rf"speaking|command of)\b[^.]{{0,40}}\b(?:{LANGUAGES_NOT_EVIDENCED})\b"
            rf"|\b(?:{LANGUAGES_NOT_EVIDENCED})\b[^.]{{0,25}}\b(?:language skills|speaker|fluency|proficiency)\b",
            re.I,
        ),
        "The CV evidences no language other than English; working in a country is not evidence of speaking its language.",
        None,
    ),
    (
        "no_us_work_authorization_claim",
        re.compile(
            r"\b(?:us|u\.s\.|american)\s+(?:citizen(?:ship)?|work authori[sz]ation|green card)\b"
            r"|\bauthori[sz]ed to work in the (?:us|u\.s\.|united states)\b",
            re.I,
        ),
        "The CV does not evidence US citizenship or US work authorization.",
        None,
    ),
    (
        "no_security_clearance_claim",
        re.compile(r"\b(?:active|current|hold(?:s|ing)?)\b[^.]{0,30}\bsecurity clearance\b|\bts/sci\b|\btop secret clearance\b", re.I),
        "The CV does not evidence any security clearance.",
        None,
    ),
    (
        "no_phd_claim",
        re.compile(rf"\b{_CLAIM_VERBS}\s+(?:[\w\s,'-]{{0,20}}\s)?ph\.?\s?d\b|\bph\.?\s?d\s+(?:graduate|holder)\b", re.I),
        "The CV evidences no PhD, held or in progress.",
        None,
    ),
    (
        "no_production_engineering_claim",
        re.compile(
            r"\b(?:years? of|my|extensive|have|has|with)\b[^.]{0,40}\b(?:production software engineering|"
            r"professional software development|backend engineering|full[- ]stack engineering)\b",
            re.I,
        ),
        "The CV does not evidence professional production software engineering experience.",
        None,
    ),
]


def validate_generated_text(text: str) -> list[ClaimViolation]:
    """Returns every anti-fabrication rule the text trips (empty = clean)."""
    text = text or ""
    violations: list[ClaimViolation] = []
    for rule, pattern, explanation, exemption in _RULES:
        for match in pattern.finditer(text):
            if exemption is not None:
                start = max(0, match.start() - CONTEXT_WINDOW_CHARS)
                end = min(len(text), match.end() + CONTEXT_WINDOW_CHARS)
                if exemption.search(text[start:end]):
                    continue
            violations.append(ClaimViolation(rule=rule, detail=explanation, matched_text=match.group(0).strip()))
            break
    return violations


def unsupported_domains() -> list[str]:
    """The CV evidence map's own list of domains Richard cannot claim."""
    return list(load_cv_evidence_map().get("explicit_non_evidence", {}).get("unsupported_domains", []))


def _in_progress_qualification() -> dict | None:
    for entry in load_cv_evidence_map().get("education", []):
        if entry.get("status") == "IN_PROGRESS":
            return entry
    return None


def msc_status_sentence() -> str:
    """The only sanctioned way to describe the MSc in generated text."""
    entry = _in_progress_qualification()
    if entry is None:
        return ""
    return (
        f"{entry['qualification']} at {entry['institution']} "
        f"({entry['dates']}) - in progress, not yet completed"
    )


def msc_study_phrase() -> str:
    """Sentence fragment for prose: safe to drop into a cover letter.

    Built from the structured education entry rather than by slicing
    msc_status_sentence() apart - the dates field itself contains " - "
    ("2024 - 2027"), so splitting on that separator truncated the letter
    mid-date and produced "(2024".
    """
    entry = _in_progress_qualification()
    if entry is None:
        return ""
    return f"{entry['qualification']} at {entry['institution']} ({entry['dates']}, in progress)"
