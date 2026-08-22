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
_LANGUAGES = (
    "arabic|russian|thai|khmer|kazakh|french|german|spanish|portuguese|italian|dutch|"
    "polish|czech|croatian|serbian|slovak|slovenian|hungarian|romanian|bulgarian|greek|"
    "turkish|hebrew|hindi|urdu|bengali|tamil|telugu|malay|indonesian|vietnamese|tagalog|"
    "filipino|korean|japanese|mandarin|cantonese|chinese|swedish|norwegian|danish|finnish|"
    "icelandic|ukrainian|persian|farsi|swahili|afrikaans|catalan|basque"
)

_MANDATORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b(?:fluen(?:t|cy)|native|bilingual|professional(?: working)? proficiency|proficient)\b"
                rf"[^.]{{0,30}}\b(?:{_LANGUAGES})\b", re.I),
     "Professional proficiency in a language other than English is required - the CV evidences English only."),
    (re.compile(rf"\b(?:{_LANGUAGES})\b[^.]{{0,20}}\b(?:speaker|speaking|native speaker|language required)\b", re.I),
     "A native/fluent speaker of a language other than English is required - the CV evidences English only."),
    (re.compile(rf"^\s*\[(?:{_LANGUAGES})\]", re.I | re.M),
     "This is a language-specific project (see the bracketed language in the title) - the CV evidences English only."),
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


@dataclass
class MismatchResult:
    mandatory_mismatches: list[str] = field(default_factory=list)
    preferred_gaps: list[str] = field(default_factory=list)


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
    return MismatchResult(mandatory_mismatches=mandatory, preferred_gaps=gaps)
