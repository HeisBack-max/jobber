"""Deterministic remote-classification + geography extraction engine.

Spec §14: use deterministic extraction first; an LLM fallback for text
deterministic extraction can't confidently resolve is a documented future
enhancement (see jobintel.geography.llm_fallback) but is NOT required to
make this engine correct - when confidence is low, the engine returns
UNCLEAR and routes to manual review rather than guessing. Never infer
worldwide remote status merely because the text contains "remote".
"""

from __future__ import annotations

import re

from jobintel.geography.country_data import (
    APAC_COUNTRIES_EXCLUDING_THAILAND,
    ASIA_COUNTRIES_EXCLUDING_THAILAND,
    CANADA_NAMES,
    EMEA_EXTRA_COUNTRIES,
    EUROPE_COUNTRIES,
    MIDDLE_EAST_COUNTRIES,
    OCCASIONAL_TRAVEL_FREQUENCY_TERMS,
    REGULAR_TRAVEL_FREQUENCY_TERMS,
    THAILAND_NAMES,
    UK_NAMES,
    US_NAMES,
)
from jobintel.models.enums import EligibilityStatus, RemoteClassification
from jobintel.models.schemas import GeographicEvidence

_US_MAJOR_CITIES = {
    "san francisco", "new york", "seattle", "austin", "chicago", "boston",
    "los angeles", "san jose", "denver", "atlanta", "washington dc", "washington, dc",
}

WORLDWIDE_RE = re.compile(
    r"remote[\s\-]*(anywhere|worldwide)|work[\s\-]+from[\s\-]+anywhere|"
    r"globally remote|fully distributed|location[\s\-]+independent|"
    r"remote[\s\-]*first,?\s*global|hire\s+globally|remote,?\s+global",
    re.I,
)

US_ONLY_RE = re.compile(
    r"remote\s*[-–—(]*\s*(united states|usa|u\.s\.a?\.?|us)\s*only\)?|"
    r"remote\s*\(\s*(united states|usa|us)\s*\)|"
    r"remote\s*[-–—,]\s*(united states|usa|us)\b(?!\s*and)|"
    r"must (reside|be located|live) in the (united states|u\.s\.a?\.?|usa)|"
    r"candidates? must (reside|be based|be located) in the (united states|usa|us)\b|"
    r"(united states|u\.s\.) residents? only|"
    r"must be (a |an )?(us|united states) citizen|"
    r"authorized to work in the (united states|us)( without sponsorship)?|"
    r"open only to candidates? (residing|located|based) in the (united states|us)|"
    r"this role is (based|located) in the united states|"
    r"must relocate to (san francisco|new york|seattle|austin|chicago|boston|"
    r"los angeles|san jose|denver|atlanta|the united states)|"
    r"48 contiguous united states",
    re.I,
)

TH_ONLY_RE = re.compile(
    r"remote\s*[-–—(]*\s*thailand\s*only\)?|"
    r"remote\s*\(\s*thailand\s*\)|"
    r"must (reside|be located|live) in thailand|"
    r"thailand residents? only|"
    r"bangkok residents? only|"
    r"must relocate to (thailand|bangkok)|"
    r"must attend the bangkok office",
    re.I,
)

HYBRID_RE = re.compile(
    r"\bhybrid\b|\d+\s*days?\s*(a|per)\s*week\s*(in|at)\s*(the\s*)?office|"
    r"remote[\s\-]friendly but expected in .* every month",
    re.I,
)

ONSITE_RE = re.compile(
    r"\bon[\s\-]?site\b|office attendance|\bin[\s\-]office\b|"
    r"must work (from|at) (the )?office|five days (a|per) week in the office|"
    r"5 days (a|per) week in the office",
    re.I,
)

TRAVEL_MENTION_RE = re.compile(
    r"travel(?:ling|ing)? (is )?required|requires? .{0,20}travel|"
    r"travel to (the )?(united states|us|thailand|[a-z ]+)|"
    r"periodic travel|regular travel|material travel|travel up to \d+%|"
    r"expected in .* every|attend the .* office",
    re.I,
)

_REGION_PATTERNS: list[tuple[re.Pattern, RemoteClassification, set[str]]] = [
    (re.compile(r"remote\s*[-–—(]*\s*(uk|united kingdom)\s*only\)?|"
                r"remote\s*\(\s*(uk|united kingdom)\s*\)", re.I),
     RemoteClassification.REMOTE_UK, UK_NAMES),
    (re.compile(r"remote\s*[-–—(]*\s*(europe|eu)\s*only\)?|eligible in europe", re.I),
     RemoteClassification.REMOTE_EUROPE, EUROPE_COUNTRIES),
    (re.compile(r"\bemea\b", re.I),
     RemoteClassification.REMOTE_EMEA, EUROPE_COUNTRIES | EMEA_EXTRA_COUNTRIES | MIDDLE_EAST_COUNTRIES),
    (re.compile(r"\bapac\b", re.I),
     RemoteClassification.REMOTE_APAC, APAC_COUNTRIES_EXCLUDING_THAILAND),
    (re.compile(r"\basia\b(?!\s*pacific)", re.I),
     RemoteClassification.REMOTE_ASIA, ASIA_COUNTRIES_EXCLUDING_THAILAND),
    (re.compile(r"middle east", re.I),
     RemoteClassification.REMOTE_MIDDLE_EAST, MIDDLE_EAST_COUNTRIES),
    (re.compile(r"remote\s*[-–—(]*\s*canada\s*only\)?", re.I),
     RemoteClassification.REMOTE_CANADA_ONLY, CANADA_NAMES),
]

# Location-field countries the candidate has excluded outright. Used to stop a
# region mentioned only in the description from overriding the location.
_EXCLUDED_OFFICE_COUNTRIES: dict[str, RemoteClassification] = {
    "United States": RemoteClassification.REMOTE_US_ONLY,
    "Thailand": RemoteClassification.REMOTE_THAILAND_ONLY,
}


def _matches(pattern: re.Pattern, text: str) -> list[str]:
    return [m.group(0) for m in pattern.finditer(text)]


def _find_countries_in_sentence(sentence: str, name_sets: dict[str, set[str]]) -> set[str]:
    found = set()
    low = sentence.lower()
    for label, names in name_sets.items():
        for name in names:
            if re.search(rf"\b{re.escape(name)}\b", low):
                found.add(label)
                break
    return found


def _extract_travel(text: str) -> tuple[bool, str | None, list[str]]:
    sentences = re.split(r"(?<=[.;\n])", text)
    travel_required = False
    frequency: str | None = None
    destinations: list[str] = []
    name_sets = {"United States": US_NAMES, "Thailand": THAILAND_NAMES}
    for sentence in sentences:
        if not TRAVEL_MENTION_RE.search(sentence):
            continue
        travel_required = True
        low = sentence.lower()
        for term in REGULAR_TRAVEL_FREQUENCY_TERMS:
            if term in low:
                frequency = term
                break
        if frequency is None:
            for term in OCCASIONAL_TRAVEL_FREQUENCY_TERMS:
                if term in low:
                    frequency = term
                    break
        for country in _find_countries_in_sentence(sentence, name_sets):
            if country not in destinations:
                destinations.append(country)
    return travel_required, frequency, destinations


def classify_geography(location_raw: str | None, description_text: str | None) -> GeographicEvidence:
    location_raw = location_raw or ""
    description_text = description_text or ""
    text = f"{location_raw}\n{description_text}"

    evidence: list[str] = []
    travel_required, travel_frequency, travel_destinations = _extract_travel(text)

    us_hits = _matches(US_ONLY_RE, text)
    th_hits = _matches(TH_ONLY_RE, text)
    worldwide_hits = _matches(WORLDWIDE_RE, text)

    if us_hits:
        evidence.append(f"US-only residency language detected: \"{us_hits[0].strip()}\"")
        return GeographicEvidence(
            classification=RemoteClassification.REMOTE_US_ONLY,
            eligible=EligibilityStatus.NO,
            confidence=0.95,
            evidence=evidence,
            required_residence_countries=["United States"],
            us_presence_required=True,
            travel_required=travel_required,
            travel_frequency=travel_frequency,
            travel_destinations=travel_destinations,
        )

    if th_hits:
        evidence.append(f"Thailand-only residency language detected: \"{th_hits[0].strip()}\"")
        return GeographicEvidence(
            classification=RemoteClassification.REMOTE_THAILAND_ONLY,
            eligible=EligibilityStatus.NO,
            confidence=0.95,
            evidence=evidence,
            required_residence_countries=["Thailand"],
            thailand_presence_required=True,
            travel_required=travel_required,
            travel_frequency=travel_frequency,
            travel_destinations=travel_destinations,
        )

    if worldwide_hits:
        evidence.append(f"Worldwide/anywhere remote language detected: \"{worldwide_hits[0].strip()}\"")
        return GeographicEvidence(
            classification=RemoteClassification.REMOTE_WORLDWIDE,
            eligible=EligibilityStatus.YES,
            confidence=0.9,
            evidence=evidence,
            permitted_residence_countries=["Worldwide"],
            travel_required=travel_required,
            travel_frequency=travel_frequency,
            travel_destinations=travel_destinations,
        )

    location_only = location_raw or ""
    for pattern, classification, permitted in _REGION_PATTERNS:
        hits = _matches(pattern, text)
        if hits:
            # A region named only in the free-text description must not override a
            # location field that contradicts it. Plenty of US-based roles merely
            # mention serving EMEA/APAC customers; without this guard those get
            # classified REMOTE_EMEA and marked eligible, surfacing roles in
            # countries the candidate has explicitly excluded.
            if not _matches(pattern, location_only):
                office = _detect_office_country(location_only)
                excluded = _EXCLUDED_OFFICE_COUNTRIES.get(office or "")
                if excluded is not None:
                    evidence.append(
                        f"{classification.value} language appears only in the description, but the "
                        f"location field ({location_only.strip()!r}) places the role in {office}; "
                        f"treating the location as authoritative."
                    )
                    return GeographicEvidence(
                        classification=excluded,
                        eligible=EligibilityStatus.NO,
                        confidence=0.8,
                        evidence=evidence,
                        required_residence_countries=[office],
                        us_presence_required=office == "United States",
                        thailand_presence_required=office == "Thailand",
                        office_country=office,
                        travel_required=travel_required,
                        travel_frequency=travel_frequency,
                        travel_destinations=travel_destinations,
                    )
            evidence.append(f"{classification.value} language detected: \"{hits[0].strip()}\"")
            return GeographicEvidence(
                classification=classification,
                eligible=EligibilityStatus.YES,
                confidence=0.75,
                evidence=evidence,
                permitted_residence_countries=sorted(permitted),
                travel_required=travel_required,
                travel_frequency=travel_frequency,
                travel_destinations=travel_destinations,
            )

    hybrid_hits = _matches(HYBRID_RE, text)
    onsite_hits = _matches(ONSITE_RE, text)
    if hybrid_hits or onsite_hits:
        office_country = _detect_office_country(text)
        classification = RemoteClassification.ONSITE if onsite_hits else RemoteClassification.HYBRID
        hit_text = (onsite_hits or hybrid_hits)[0].strip()
        evidence.append(f"{classification.value} language detected: \"{hit_text}\"")
        if office_country:
            evidence.append(f"Office location detected: {office_country}")
        eligible = EligibilityStatus.UNCLEAR
        if office_country in ("United States", "Thailand"):
            eligible = EligibilityStatus.NO
        elif office_country:
            eligible = EligibilityStatus.YES
        return GeographicEvidence(
            classification=classification,
            eligible=eligible,
            confidence=0.8 if office_country else 0.5,
            evidence=evidence,
            physical_office_requirement=True,
            office_country=office_country,
            us_presence_required=office_country == "United States",
            thailand_presence_required=office_country == "Thailand",
            travel_required=travel_required,
            travel_frequency=travel_frequency,
            travel_destinations=travel_destinations,
        )

    if travel_required and (travel_destinations or "remote" in text.lower()):
        evidence.append("Remote-style language present but no confident residency/classification signal found; travel language detected.")
        return GeographicEvidence(
            classification=RemoteClassification.UNCLEAR,
            eligible=EligibilityStatus.UNCLEAR,
            confidence=0.35,
            evidence=evidence,
            travel_required=travel_required,
            travel_frequency=travel_frequency,
            travel_destinations=travel_destinations,
        )

    if "remote" in text.lower():
        evidence.append("Contains the word 'remote' but no specific scope (worldwide/region/country) could be confidently extracted.")
        return GeographicEvidence(
            classification=RemoteClassification.UNCLEAR,
            eligible=EligibilityStatus.UNCLEAR,
            confidence=0.3,
            evidence=evidence,
        )

    evidence.append("No remote/location eligibility language detected.")
    return GeographicEvidence(
        classification=RemoteClassification.UNCLEAR,
        eligible=EligibilityStatus.UNCLEAR,
        confidence=0.2,
        evidence=evidence,
    )


def _detect_office_country(text: str) -> str | None:
    low = text.lower()
    for name in US_NAMES | _US_MAJOR_CITIES:
        if re.search(rf"\b{re.escape(name)}\b", low):
            return "United States"
    for name in THAILAND_NAMES:
        if re.search(rf"\b{re.escape(name)}\b", low):
            return "Thailand"
    for name in UK_NAMES | {"london"}:
        if re.search(rf"\b{re.escape(name)}\b", low):
            return "United Kingdom"
    for name in EUROPE_COUNTRIES:
        if re.search(rf"\b{re.escape(name)}\b", low):
            return name.title()
    return None
