"""Semantic role-family matching (spec §9/§10).

A vacancy does not need to use the same terminology as the CV - matching
combines fuzzy title similarity with keyword overlap against each role
family's example titles, rather than requiring an exact title match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from jobintel.settings import load_roles

_STOPWORDS = {
    "the", "and", "or", "of", "a", "an", "for", "in", "on", "to", "with",
    "specialist", "trainer", "training",
}

_TIER_WEIGHT = {"A": 1.0, "B": 0.9, "C": 0.8, "dedicated_channel": 0.9}


@dataclass
class RoleMatchResult:
    role_family: str | None
    tier: str | None
    label: str | None
    title_score: float  # 0-1
    keyword_score: float  # 0-1
    combined_score: float  # 0-1
    evidence_categories: list[str] = field(default_factory=list)
    matched_example_title: str | None = None


def _keywords_from_titles(titles: list[str]) -> set[str]:
    words: set[str] = set()
    for title in titles:
        for word in re.findall(r"[a-zA-Z]+", title.lower()):
            if len(word) > 3 and word not in _STOPWORDS:
                words.add(word)
    return words


def match_role_family(job_title: str, description_text: str) -> RoleMatchResult:
    roles = load_roles().get("role_families", {})
    description_lower = (description_text or "").lower()
    title_lower = (job_title or "").lower()

    best: RoleMatchResult | None = None
    for family_key, family in roles.items():
        example_titles = family.get("example_titles", [])
        if not example_titles:
            continue

        best_title_ratio = 0.0
        best_title = None
        for example in example_titles:
            ratio = fuzz.token_set_ratio(title_lower, example.lower()) / 100.0
            if ratio > best_title_ratio:
                best_title_ratio = ratio
                best_title = example

        keywords = _keywords_from_titles(example_titles)
        if keywords:
            hits = sum(1 for kw in keywords if kw in description_lower)
            keyword_score = min(1.0, hits / max(3, len(keywords) * 0.3))
        else:
            keyword_score = 0.0

        combined = (best_title_ratio * 0.65) + (keyword_score * 0.35)
        combined *= _TIER_WEIGHT.get(family.get("tier"), 0.75)

        if best is None or combined > best.combined_score:
            best = RoleMatchResult(
                role_family=family_key,
                tier=family.get("tier"),
                label=family.get("label"),
                title_score=best_title_ratio,
                keyword_score=keyword_score,
                combined_score=combined,
                evidence_categories=family.get("evidence_categories", []),
                matched_example_title=best_title,
            )

    if best is None or best.combined_score < 0.12:
        return RoleMatchResult(
            role_family=None, tier=None, label=None,
            title_score=0.0, keyword_score=0.0, combined_score=0.0,
        )
    return best
