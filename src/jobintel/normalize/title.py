"""Title normalization and seniority extraction (spec §50)."""

from __future__ import annotations

import re

from jobintel.models.enums import SeniorityLevel

_SENIORITY_PATTERNS: list[tuple[re.Pattern, SeniorityLevel]] = [
    (re.compile(r"\bintern(ship)?\b", re.I), SeniorityLevel.INTERNSHIP),
    (re.compile(r"\bentry[\s-]level\b", re.I), SeniorityLevel.ENTRY),
    (re.compile(r"\bjunior\b|\bjr\.?\b", re.I), SeniorityLevel.JUNIOR),
    (re.compile(r"\bexecutive\b|\bc-level\b|\bchief\b", re.I), SeniorityLevel.EXECUTIVE),
    (re.compile(r"\bhead of\b", re.I), SeniorityLevel.HEAD),
    (re.compile(r"\bdirector\b", re.I), SeniorityLevel.DIRECTOR),
    (re.compile(r"\bmanager\b", re.I), SeniorityLevel.MANAGER),
    (re.compile(r"\bprincipal\b", re.I), SeniorityLevel.PRINCIPAL),
    (re.compile(r"\blead\b", re.I), SeniorityLevel.LEAD),
    (re.compile(r"\bsenior\b|\bsr\.?\b", re.I), SeniorityLevel.SENIOR),
    (re.compile(r"\bmid[\s-]level\b", re.I), SeniorityLevel.MID),
]


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title or "").strip()
    cleaned = re.sub(r"\s*[\(\[].*?(remote|hybrid|onsite|contract|full[- ]time|part[- ]time).*?[\)\]]", "", cleaned, flags=re.I)
    return cleaned.strip(" -|")


def detect_seniority(title: str) -> SeniorityLevel:
    for pattern, level in _SENIORITY_PATTERNS:
        if pattern.search(title or ""):
            return level
    return SeniorityLevel.UNSPECIFIED
