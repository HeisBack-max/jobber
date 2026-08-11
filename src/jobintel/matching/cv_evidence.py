"""Looks up CV-grounded evidence text for a set of evidence categories.

Every explanation the app shows Richard must be traceable to a real
entry in config/cv_evidence_map.json - never generic AI filler
(spec §27/§28).
"""

from __future__ import annotations

from jobintel.settings import load_cv_evidence_map


def get_evidence_for_categories(categories: list[str], limit_per_category: int = 2) -> list[str]:
    evidence_map = load_cv_evidence_map().get("evidence_categories", {})
    texts: list[str] = []
    for category in categories:
        entries = evidence_map.get(category, [])
        for entry in entries[:limit_per_category]:
            text = entry.get("text", "")
            employer = entry.get("employer")
            suffix = f" ({employer})" if employer else ""
            texts.append(f"{text}{suffix}")
    return texts


def has_any_evidence(categories: list[str]) -> bool:
    evidence_map = load_cv_evidence_map().get("evidence_categories", {})
    return any(evidence_map.get(c) for c in categories)
