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


@dataclass
class MismatchResult:
    mandatory_mismatches: list[str] = field(default_factory=list)
    preferred_gaps: list[str] = field(default_factory=list)


def find_mismatches(description_text: str) -> MismatchResult:
    text = description_text or ""
    mandatory = []
    for pattern, message in _MANDATORY_PATTERNS:
        if pattern.search(text):
            mandatory.append(message)
    gaps = []
    for pattern, message in _PREFERRED_GAP_PATTERNS:
        if pattern.search(text):
            gaps.append(message)
    return MismatchResult(mandatory_mismatches=mandatory, preferred_gaps=gaps)
