"""Negative matching (spec §11): distinguishes MANDATORY_MISMATCH (fatal,
unless CV-supported) from PREFERRED_REQUIREMENT_GAP (notable, non-fatal).

Curated regexes rather than literal substring search against
roles.yaml's example signal strings, because real postings phrase these
requirements in many different ways. roles.yaml's signal lists document
*intent*; this module is the deterministic-first implementation of that
intent (mirrors the geography engine's approach, spec §14).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Languages the CV does not evidence. Richard has worked extensively in
# non-English-speaking countries (Qatar, Kazakhstan, Thailand, Cambodia),
# and the CV evidences no language other than English - so a posting that
# *requires* another language is a genuine mandatory mismatch, not a soft
# gap. This matters in practice: the AI-data marketplaces publish large
# numbers of language-specific contractor projects ("[Croatian] - Voice
# Recording Specialist"), which would otherwise all read as plausible
# gig matches.
LANGUAGES_NOT_EVIDENCED = (
    "arabic|russian|thai|khmer|kazakh|french|german|spanish|portuguese|italian|dutch|"
    "polish|czech|croatian|serbian|slovak|slovenian|hungarian|romanian|bulgarian|greek|"
    "turkish|hebrew|hindi|urdu|bengali|tamil|telugu|malay|indonesian|vietnamese|tagalog|"
    "filipino|korean|japanese|mandarin|cantonese|chinese|swedish|norwegian|danish|finnish|"
    "icelandic|ukrainian|persian|farsi|swahili|afrikaans|catalan|basque"
)

_MANDATORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(7|8|9|10)\+?\s*years?\b.{0,40}(software engineering|full-stack|backend engineering|production engineering)", re.I | re.S),
     "8+ years of full-time production software engineering required - not supported by the CV."),
    (re.compile(r"\bproduction\b.{0,20}\bkubernetes\b|\bdeep\b.{0,20}\bkubernetes\b", re.I | re.S),
     "Deep production Kubernetes engineering experience required - not supported by the CV."),
    (re.compile(r"active (us |u\.s\. )?(top secret|secret|ts/sci|security clearance)", re.I | re.S),
     "Active US security clearance required - not supported by the CV."),
    (re.compile(r"\bmust be (a |an )?(us|u\.s\.) citizen\b|\bu\.s\.? citizenship required\b", re.I | re.S),
     "US citizenship required - not supported by the CV."),
    (re.compile(r"\b(medical licen[sc]e|licensed physician|registered nurse licen[sc]e)\b", re.I | re.S),
     "Medical licence required - not supported by the CV."),
    (re.compile(r"\bph\.?d\.?\s*(is )?required\b|\bmandatory ph\.?d\.?\b", re.I | re.S),
     "Mandatory PhD required - not supported by the CV."),
    (re.compile(r"\b(completed |required to have a )?master'?s degree (is )?required\b|\bmandatory master'?s degree\b", re.I | re.S),
     "A completed master's degree is required - Richard's MSc Data Analytics is in progress, not complete."),
    (re.compile(r"\bsoc\b.{0,20}(analyst|operations).{0,20}(required|experience)", re.I | re.S),
     "Deep SOC operations experience required - not supported by the CV."),
    (re.compile(r"\bsenior\b.{0,20}cloud architect(ure)?\b.{0,20}(required|experience)", re.I | re.S),
     "Senior cloud architecture experience required - not supported by the CV."),
    (re.compile(r"\bpublished (research|papers)\b|\bpeer-reviewed publications?\b.{0,20}required", re.I | re.S),
     "Professional ML research/publication history required - not supported by the CV."),
    (re.compile(r"\bdaily office attendance\b|\bmust be in the office every day\b", re.I | re.S),
     "Mandatory daily office attendance required."),
]

_PREFERRED_GAP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bpreferred\b.{0,30}(certification|certified)", re.I | re.S),
     "A preferred certification is listed - not currently held per the CV."),
    (re.compile(r"\bnice to have\b.{0,30}(cloud|aws|azure|gcp|certification)", re.I | re.S),
     "A nice-to-have cloud/vendor certification is listed - not currently held per the CV."),
    (re.compile(r"\bfamiliarity with\b.{0,40}(lms|learning management system)", re.I | re.S),
     "Familiarity with a specific proprietary LMS is preferred - not evidenced in the CV."),
    (re.compile(r"\bpreferred\b.{0,30}(additional )?language\b", re.I | re.S),
     "An additional preferred language is listed - the CV does not evidence another language."),
]


# A language is only a mismatch when the posting *requires* it. Matching
# on the language name alone produced false mandatory mismatches on
# postings that require nothing but English - "Fluent English required;
# German is a plus", "you will support our Spanish speaking customers",
# even "proficient with French press coffee machines". A mandatory
# mismatch hard-caps the score at 55, so each of those silently deleted a
# perfectly eligible role from the feed, and the tailoring generator then
# quoted the invented requirement back at the employer in a cover letter.
_REQUIREMENT_MARKER = re.compile(
    r"\b(?:require[sd]?|required|requirement|must\s+(?:be|have|possess|speak)|mandatory|essential|"
    r"looking for|seeking|hiring|need(?:s|ed)?\s+to\s+(?:be|have|speak)|you\s+(?:will\s+)?need)\b",
    re.I,
)
_OPTIONAL_MARKER = re.compile(
    r"\b(?:a plus|nice to have|nice-to-have|preferred|preferable|advantageous|an advantage|bonus|"
    r"desirable|ideally|would be great|welcome)\b",
    re.I,
)
_LANGUAGE_CONTEXT = re.compile(
    rf"\b(?:fluen(?:t|cy)|native|native-level|bilingual|proficien\w*|business-level|speaker|speaking|"
    rf"command of|written and spoken)\b[^,;.]{{0,40}}\b(?:{LANGUAGES_NOT_EVIDENCED})\b"
    rf"|\b(?:{LANGUAGES_NOT_EVIDENCED})\b[^,;.]{{0,25}}\b(?:fluen(?:t|cy)|native|speaker|speaking|"
    rf"proficien\w*|language|skills)\b",
    re.I,
)
_BRACKETED_LANGUAGE_TITLE = re.compile(rf"^\s*\[(?:{LANGUAGES_NOT_EVIDENCED})\]", re.I | re.M)
_CLAUSE_SPLIT = re.compile(r"[.;\n•|]+")

_LANGUAGE_MANDATORY_MESSAGE = (
    "Requires professional proficiency in a language other than English - the CV evidences "
    "English only."
)
_LANGUAGE_PREFERRED_MESSAGE = (
    "A language other than English is listed as preferred/nice-to-have - the CV evidences "
    "English only."
)


def _language_requirements(text: str) -> tuple[list[str], list[str]]:
    """Split into clauses first: requirement words bind to their own
    clause, so "Fluent English required; German is a plus" must not read
    as "German required"."""
    mandatory: list[str] = []
    preferred: list[str] = []

    if _BRACKETED_LANGUAGE_TITLE.search(text):
        mandatory.append(
            "This is a language-specific project (see the bracketed language in the title) - "
            "the CV evidences English only."
        )

    for clause in _CLAUSE_SPLIT.split(text):
        if not _LANGUAGE_CONTEXT.search(clause):
            continue
        if _OPTIONAL_MARKER.search(clause):
            if _LANGUAGE_PREFERRED_MESSAGE not in preferred:
                preferred.append(_LANGUAGE_PREFERRED_MESSAGE)
        elif _REQUIREMENT_MARKER.search(clause):
            if _LANGUAGE_MANDATORY_MESSAGE not in mandatory:
                mandatory.append(_LANGUAGE_MANDATORY_MESSAGE)

    return mandatory, preferred


# Short noun phrases for each mandatory-mismatch message, for use in
# generated prose. The messages themselves are full explanatory
# sentences ("A completed master's degree is required - Richard's MSc
# ... is in progress"), which read as nonsense when dropped into a
# sentence: "it calls for a completed master's degree is required".
_REQUIREMENT_PHRASES: dict[str, str] = {
    '8+ years of full-time production software engineering required': '8+ years of production software engineering',
    'Deep production Kubernetes engineering experience required': 'deep production Kubernetes engineering experience',
    'Active US security clearance required': 'an active US security clearance',
    'US citizenship required': 'US citizenship',
    'Medical licence required': 'a medical licence',
    'Mandatory PhD required': 'a PhD', "A completed master's degree is required": "a completed master's degree", 'Deep SOC operations experience required': 'deep SOC operations experience',
    'Senior cloud architecture experience required': 'senior cloud architecture experience',
    'Professional ML research/publication history required': 'a professional ML research/publication history',
    'Mandatory daily office attendance required': 'daily office attendance',
    'Requires professional proficiency in a language other than English': 'professional proficiency in a language other than English',
}


def requirement_phrase(message: str) -> str:
    """A noun phrase for a mismatch message, for use mid-sentence."""
    for prefix, phrase in _REQUIREMENT_PHRASES.items():
        if message.startswith(prefix):
            return phrase
    # Fall back to the clause before the explanation, lower-cased.
    return message.split(" - ")[0].rstrip(".").lower()


@dataclass
class MismatchResult:
    mandatory_mismatches: list[str] = field(default_factory=list)
    preferred_gaps: list[str] = field(default_factory=list)

    @property
    def mandatory_requirement_phrases(self) -> list[str]:
        return [requirement_phrase(m) for m in self.mandatory_mismatches]


def find_mismatches(description_text: str, job_title: str | None = None) -> MismatchResult:
    """The title is matched too, not just the description: a
    language-specific contractor project frequently carries its only
    language marker in the title ("[Croatian] - Voice Recording
    Specialist") and says nothing about it in the body."""
    text = "\n".join(part for part in (job_title, description_text) if part)
    mandatory = []
    for pattern, message in _MANDATORY_PATTERNS:
        if pattern.search(text):
            mandatory.append(message)
    gaps = []
    for pattern, message in _PREFERRED_GAP_PATTERNS:
        if pattern.search(text):
            gaps.append(message)

    language_mandatory, language_preferred = _language_requirements(text)
    return MismatchResult(
        mandatory_mismatches=mandatory + language_mandatory,
        preferred_gaps=gaps + language_preferred,
    )
