"""Semantic role-family matching (spec §9/§10).

A vacancy does not need to use the same terminology as the CV - matching
combines fuzzy title similarity with keyword overlap against each role
family's example titles, rather than requiring an exact title match.

False-positive guard (spec §51): generic business words like
"enablement", "adoption", or "education" appear in role titles across
every industry (GTM enablement, sales enablement, partner enablement -
none of which are AI/cybersecurity roles), and a single shared token can
otherwise drag the fuzzy title ratio up enough to look like a real match.
For the AI/cybersecurity-specific families, a real anchor term must
appear in the job title itself (not just company boilerplate in the
description, which mentions "AI" in the About-Us section of nearly every
AI company's job postings regardless of the role) before that family is
eligible to win.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from jobintel.settings import load_roles

_STOPWORDS = {
    "the", "and", "or", "of", "a", "an", "for", "in", "on", "to", "with",
    "specialist", "trainer", "training",
    # Generic business/role nouns that appear across unrelated industries
    # and would otherwise falsely anchor a match via a single shared token
    # (e.g. "GTM Enablement" vs. "AI Enablement Specialist").
    "enablement", "adoption", "education", "curriculum", "consulting",
    "consultant", "learning", "solutions", "customer", "success",
    "developer", "designer", "programme", "program", "manager", "lead",
    "coordinator", "advisor", "officer",
}

_TIER_WEIGHT = {"A": 1.0, "B": 0.9, "C": 0.8, "dedicated_channel": 0.9}

_MIN_COMBINED_SCORE = 0.40

# rapidfuzz's token_set_ratio has a character-level fuzzy component and
# can score moderately (0.4-0.55) even between titles sharing zero real
# words (observed: "International Indirect Tax, VAT/GST" vs. "Technical
# Instructional Designer" scored 0.51). A hard floor keeps a spuriously
# medium title score from being a candidate at all - keyword hits on
# generic job-posting boilerplate ("experience", "technical") must not
# be able to single-handedly promote an unrelated title into a match.
_MIN_TITLE_RATIO = 0.60

# Families whose Tier-A/dedicated positioning depends on the role
# genuinely being about AI or cybersecurity, not just sharing a generic
# business word with one of the example titles.
_ANCHOR_TERMS: dict[str, re.Pattern] = {
    "ai_training": re.compile(r"\bai\b|artificial intelligence|generative ai|\bllm\b|machine learning|\bgemini\b|vertex ai", re.I),
    "ai_security": re.compile(r"\bai\b|\bllm\b|red.?team|adversarial|jailbreak|prompt injection", re.I),
    "ai_evaluation": re.compile(r"\bai\b|\bllm\b|evaluat|model (safety|robustness)", re.I),
    "prompt_engineering": re.compile(r"prompt engineer|\bllm\b|\bai\b", re.I),
    "cybersecurity_training": re.compile(r"cyber ?security|penetration test|\bosint\b|\bgrc\b|red.?team|security awareness", re.I),
    "cybersecurity_consulting": re.compile(r"cyber ?security|\bosint\b|\bgrc\b|security awareness", re.I),
    "google_vertex_ai": re.compile(r"\bvertex ai\b|\bgemini\b|google cloud", re.I),
}

# "ai_training" is the catch-all AI family (its own anchor is satisfied
# by the bare word "ai" alone), so on a title contested by a more
# specific AI sub-family it should lose the tie-break rather than win on
# a coincidental token overlap (observed: "AI Security Enablement Lead"
# out-scored ai_security's own best example title purely because "AI
# Enablement Specialist" shares the word "enablement"). Titles carrying
# one of these more specific signals get ai_training deprioritized.
_MORE_SPECIFIC_THAN_AI_TRAINING = re.compile(
    r"security|red.?team|adversarial|jailbreak|evaluat|\bosint\b|\bgrc\b|"
    r"penetration test|prompt engineer|vertex ai|\bgemini\b",
    re.I,
)


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


def _strip_stopwords(text: str) -> str:
    """Used before fuzzy title comparison, not just keyword extraction -
    generic words like "enablement" appear in example titles across
    Tier A, B, *and* C (AI Enablement Specialist / Technical Enablement
    Specialist / Customer Enablement - AI), so per-family anchor gating
    alone can't close this: a title like "GTM Enablement - Expansion"
    would still fuzzy-match "Customer Enablement - AI" at a high ratio
    purely on the shared word "enablement". Stripping stopwords from both
    sides before comparing removes that shared token everywhere at once."""
    words = [w for w in re.findall(r"[a-zA-Z]+", text.lower()) if w not in _STOPWORDS]
    return " ".join(words)


def _passes_anchor_gate(family_key: str, title_lower: str) -> bool:
    """No fuzzy-ratio fallback here on purpose: a high title_ratio can be
    driven entirely by one coincidentally shared generic word (observed:
    "AV Engineer" scored 0.84 against "Prompt Engineer" purely from the
    shared token "engineer"). For an anchor-gated family, the anchor term
    itself must actually appear in the title - no exceptions."""
    anchor = _ANCHOR_TERMS.get(family_key)
    if anchor is None:
        return True  # not an anchor-gated family (Tier B/C are intentionally broader)
    return bool(anchor.search(title_lower))


def match_role_family(job_title: str, description_text: str) -> RoleMatchResult:
    roles = load_roles().get("role_families", {})
    description_lower = (description_text or "").lower()
    title_lower = (job_title or "").lower()

    title_stripped = _strip_stopwords(title_lower)

    candidates: list[RoleMatchResult] = []
    for family_key, family in roles.items():
        example_titles = family.get("example_titles", [])
        if not example_titles:
            continue

        best_title_ratio = 0.0
        best_title = None
        for example in example_titles:
            example_stripped = _strip_stopwords(example)
            if not title_stripped or not example_stripped:
                continue
            ratio = fuzz.token_set_ratio(title_stripped, example_stripped) / 100.0
            if ratio > best_title_ratio:
                best_title_ratio = ratio
                best_title = example

        if best_title_ratio < _MIN_TITLE_RATIO:
            continue
        if not _passes_anchor_gate(family_key, title_lower):
            continue

        keywords = _keywords_from_titles(example_titles)
        if keywords:
            hits = sum(1 for kw in keywords if kw in description_lower)
            keyword_score = min(1.0, hits / max(3, len(keywords) * 0.3))
        else:
            keyword_score = 0.0

        # Keyword hits act as a bonus on top of a real title match, not
        # an independent channel that can carry the score alone - this
        # is what the title floor above already mostly guarantees, but
        # weighting title higher keeps keyword noise from inflating
        # borderline-floor titles further.
        combined = (best_title_ratio * 0.75) + (keyword_score * 0.25)
        combined *= _TIER_WEIGHT.get(family.get("tier"), 0.75)
        if family_key == "ai_training" and _MORE_SPECIFIC_THAN_AI_TRAINING.search(title_lower):
            combined *= 0.8

        candidates.append(RoleMatchResult(
            role_family=family_key,
            tier=family.get("tier"),
            label=family.get("label"),
            title_score=best_title_ratio,
            keyword_score=keyword_score,
            combined_score=combined,
            evidence_categories=family.get("evidence_categories", []),
            matched_example_title=best_title,
        ))

    if not candidates:
        return RoleMatchResult(
            role_family=None, tier=None, label=None,
            title_score=0.0, keyword_score=0.0, combined_score=0.0,
        )

    best = max(candidates, key=lambda c: c.combined_score)
    if best.combined_score < _MIN_COMBINED_SCORE:
        return RoleMatchResult(
            role_family=None, tier=None, label=None,
            title_score=0.0, keyword_score=0.0, combined_score=0.0,
        )
    return best
