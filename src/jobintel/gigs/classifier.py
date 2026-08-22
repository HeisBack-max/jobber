"""Recognises gig/project work inside ordinary collected postings.

The gig channel was originally blocked on Outlier AI, which has no
public listing API (see outlier.py). But gig work is not only listed on
gig platforms: the AI-data marketplaces already collected through their
public ATS boards - Appen, Mercor, Toloka, Turing, Invisible, Prolific,
Labelbox - post independent-contractor project work on the very same
board as their staff roles. "[Croatian] - Voice Recording Specialist:
Join our team as an Independent Contractor for Project Morava" arrives
through the ordinary Lever collector.

So the working, ToS-compliant gig channel is a classifier over postings
this app already collects legitimately, not a scraper against a
login-only platform. This module decides whether a posting is gig work
and extracts the fields career postings don't carry: hourly rate,
expected weekly hours, and project duration.

Deliberately conservative: misclassifying a permanent role as a gig
would route it through gig scoring, where a salaried job with no hourly
rate scores badly for reasons that have nothing to do with its merit. A
posting has to show a real contractor/project signal, not just contain
the word "contract".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobintel.normalize.salary import parse_salary

# Self-referential signals: the posting says *this position* is contract
# or project work. Any one of these is sufficient on its own.
#
# The distinction matters, and only showed up against real postings: an
# Anthropic "Hardware Lab Manager" describes overseeing "contractor work
# on-site (electricians, cabling crews)", and an accounts-receivable role
# mentions "as-needed" support. Both were classified as gigs by an
# earlier version of this module that treated any mention of contract
# work as a strong signal. A posting has to describe *itself* as
# contract work, not merely mention contractors.
_SELF_REFERENTIAL_GIG_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bindependent contractor\b", re.I), "described as independent contractor work"),
    (re.compile(r"\b(?:this|the)\s+(?:is\s+an?\s+|role\s+is\s+an?\s+|position\s+is\s+an?\s+)[^.]{0,40}"
                r"(?:contract|contractor|freelance|temporary|project)[^.]{0,20}"
                r"(?:position|role|assignment|engagement|opportunity|basis)\b", re.I),
     "posting describes itself as contract/project work"),
    (re.compile(r"\bcontract(?:or)? (?:role|position|assignment|engagement|opportunity)\b", re.I),
     "advertised as a contract role"),
    (re.compile(r"\bfreelance (?:role|position|opportunity|contract|basis|work)\b|\bon a freelance basis\b", re.I),
     "advertised as freelance"),
    (re.compile(r"\bgig\b(?!\w)", re.I), "described as gig work"),
    (re.compile(r"\bper[- ]project\b|\bpaid per project\b", re.I), "paid per project"),
    (re.compile(r"\bshort[- ]term (?:project|engagement|contract)\b", re.I), "short-term engagement"),
]

# Supporting signals: real but ambiguous on their own. A permanent role
# can legitimately be part-time, mention contributors, or offer flexible
# hours, so these only count in combination.
_SUPPORTING_GIG_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfreelance\b", re.I), "mentions freelance"),
    (re.compile(r"\bproject[- ]based\b", re.I), "described as project-based"),
    (re.compile(r"\bhourly rate\b|\bpaid hourly\b|\bper hour\b|\b/\s?(?:hour|hr)\b", re.I), "paid by the hour"),
    (re.compile(r"\bflexible hours\b|\bwork on your own schedule\b|\bset your own hours\b", re.I), "self-scheduled"),
    (re.compile(r"\bpart[- ]time\b", re.I), "part-time"),
    (re.compile(r"\bas[- ]needed\b|\bad[- ]hoc\b", re.I), "as-needed work"),
    (re.compile(r"\bno (?:minimum|fixed) (?:hours|commitment)\b", re.I), "no fixed hours commitment"),
]

# Phrasing that rules a posting *out*, even if a stray "contract" appears
# (permanent roles routinely mention contract terms, contractor
# management, or contract law).
_NOT_A_GIG_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bfull[- ]time (?:permanent|employee|position|role)\b", re.I),
    re.compile(r"\bpermanent (?:role|position|contract of employment)\b", re.I),
    re.compile(r"\bsalary (?:range|band)\b.{0,30}\bper (?:year|annum)\b", re.I),
    re.compile(r"\bcontract (?:law|management|negotiation|lifecycle|manager)\b", re.I),
]

_HOURLY_RATE_RE = re.compile(
    r"(?P<currency>[$£€])?\s?(?P<low>\d{1,4}(?:\.\d{1,2})?)\s*(?:-|–|to)\s*(?P<currency2>[$£€])?\s?"
    r"(?P<high>\d{1,4}(?:\.\d{1,2})?)\s*(?:per hour|/\s?hour|/\s?hr|an hour|hourly)",
    re.I,
)
_SINGLE_RATE_RE = re.compile(
    r"(?P<currency>[$£€])?\s?(?P<value>\d{1,4}(?:\.\d{1,2})?)\s*(?:per hour|/\s?hour|/\s?hr|an hour|hourly)",
    re.I,
)
_WEEKLY_HOURS_RE = re.compile(
    r"(?P<low>\d{1,2})\s*(?:-|–|to)\s*(?P<high>\d{1,2})\s*hours?\s*(?:per|a|/)\s*week",
    re.I,
)
_SINGLE_WEEKLY_HOURS_RE = re.compile(r"(?:up to\s*)?(?P<value>\d{1,2})\s*hours?\s*(?:per|a|/)\s*week", re.I)
_DURATION_RE = re.compile(
    r"\b(?P<value>\d{1,2})\s*(?P<unit>week|weeks|month|months)\b[^.]{0,30}"
    r"(?:project|engagement|contract|assignment)|"
    r"(?:project|engagement|contract|assignment)[^.]{0,30}\b(?P<value2>\d{1,2})\s*(?P<unit2>week|weeks|month|months)\b",
    re.I,
)


@dataclass
class GigSignals:
    is_gig: bool
    reasons: list[str] = field(default_factory=list)
    hourly_rate_min: float | None = None
    hourly_rate_max: float | None = None
    rate_currency: str | None = None
    weekly_hours_min: float | None = None
    weekly_hours_max: float | None = None
    project_duration: str | None = None


def _currency_of(*symbols: str | None) -> str | None:
    mapping = {"$": "USD", "£": "GBP", "€": "EUR"}
    for symbol in symbols:
        if symbol and symbol in mapping:
            return mapping[symbol]
    return None


def extract_hourly_rate(text: str) -> tuple[float | None, float | None, str | None]:
    match = _HOURLY_RATE_RE.search(text or "")
    if match:
        return (
            float(match.group("low")),
            float(match.group("high")),
            _currency_of(match.group("currency"), match.group("currency2")),
        )
    match = _SINGLE_RATE_RE.search(text or "")
    if match:
        value = float(match.group("value"))
        return value, value, _currency_of(match.group("currency"))
    return None, None, None


def extract_weekly_hours(text: str) -> tuple[float | None, float | None]:
    match = _WEEKLY_HOURS_RE.search(text or "")
    if match:
        return float(match.group("low")), float(match.group("high"))
    match = _SINGLE_WEEKLY_HOURS_RE.search(text or "")
    if match:
        return None, float(match.group("value"))
    return None, None


def extract_duration(text: str) -> str | None:
    match = _DURATION_RE.search(text or "")
    if not match:
        return None
    value = match.group("value") or match.group("value2")
    unit = match.group("unit") or match.group("unit2")
    if not value or not unit:
        return None
    return f"{value} {unit if unit.endswith('s') else unit + 's'}"


def classify_gig(job_title: str, description_text: str, employment_type: str | None = None,
                 salary_raw: str | None = None) -> GigSignals:
    """Decide whether a collected posting is gig/project work."""
    text = f"{job_title or ''}\n{description_text or ''}"

    if any(pattern.search(text) for pattern in _NOT_A_GIG_PATTERNS):
        return GigSignals(is_gig=False, reasons=["posting describes permanent/salaried employment"])

    self_referential = [reason for pattern, reason in _SELF_REFERENTIAL_GIG_PATTERNS if pattern.search(text)]
    supporting = [reason for pattern, reason in _SUPPORTING_GIG_PATTERNS if pattern.search(text)]

    # `employment_type` is derived by a loose regex over the description
    # (normalize/normalizer.py), so it is corroboration, never proof.
    if employment_type in {"FREELANCE", "CONTRACT"}:
        supporting.append(f"employment type detected as {employment_type.lower()}")

    hourly_min, hourly_max, currency = extract_hourly_rate(text)
    if hourly_min is None and salary_raw:
        parsed = parse_salary(salary_raw)
        if parsed.salary_period == "hourly":
            hourly_min, hourly_max, currency = parsed.salary_min, parsed.salary_max, parsed.salary_currency
            supporting.append("compensation quoted as an hourly rate")

    weekly_min, weekly_max = extract_weekly_hours(text)

    # Sufficient: the posting calls itself contract/project work, or it
    # quotes an hourly rate and shows at least one other gig signal.
    # Otherwise a pile of weak signals has to be genuinely convincing.
    is_gig = (
        bool(self_referential)
        or (hourly_min is not None and len(supporting) >= 2)
        or len(supporting) >= 4
    )

    return GigSignals(
        is_gig=is_gig,
        reasons=self_referential + supporting,
        hourly_rate_min=hourly_min,
        hourly_rate_max=hourly_max,
        rate_currency=currency,
        weekly_hours_min=weekly_min,
        weekly_hours_max=weekly_max,
        project_duration=extract_duration(text),
    )


# Platforms whose ATS boards are known to carry contractor project work
# alongside staff roles. Used only to set the gig scorer's
# `platform_reliability` input - never to classify a posting as a gig,
# which is always decided from the posting's own text.
PLATFORM_RELIABILITY: dict[str, float] = {
    "appen": 0.7,
    "mercor": 0.75,
    "toloka": 0.7,
    "turing": 0.75,
    "invisible technologies": 0.7,
    "prolific": 0.8,
    "labelbox": 0.75,
    "scale ai": 0.75,
    "snorkel ai": 0.75,
    "toptal": 0.7,
    "andela": 0.7,
}
DEFAULT_PLATFORM_RELIABILITY = 0.6


def platform_reliability_for(company_name: str) -> float:
    return PLATFORM_RELIABILITY.get((company_name or "").strip().lower(), DEFAULT_PLATFORM_RELIABILITY)
