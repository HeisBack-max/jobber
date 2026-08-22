"""CV-tailoring briefs and cover-letter drafts (spec §39).

Design rule, and the reason this is not just a prompt: the deterministic
generator can only emit sentences assembled from entries that exist in
config/cv_evidence_map.json, and every generated document records the
evidence ids it used. An LLM may then *rewrite* that draft for tone, but
it is validated against the same anti-fabrication rules afterwards and
discarded if it invents anything (see guardrails.py). The system never
sends Richard a document containing a claim it cannot point at a line of
his real CV for.

What the brief contains, in order of what is actually useful when
applying:

  * which CV evidence to foreground, ranked by similarity to *this*
    posting rather than by CV order,
  * which of the posting's requirements have no CV support at all, so
    Richard sees them before an interviewer does,
  * the posting's own vocabulary that his evidence genuinely supports
    (ATS keyword mirroring that isn't keyword stuffing), and
  * the honest statement of the MSc's in-progress status.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jobintel.matching.embeddings import cosine_similarity, get_role_family_index
from jobintel.matching.negative_matcher import find_mismatches
from jobintel.matching.role_matcher import match_role_family
from jobintel.settings import load_cv_evidence_map, load_profile
from jobintel.tailoring.guardrails import (
    ClaimViolation,
    msc_status_sentence,
    msc_study_phrase,
    unsupported_domains,
    validate_generated_text,
)

MAX_EVIDENCE_ITEMS = 6
MIN_EVIDENCE_SIMILARITY = 0.02


@dataclass
class EvidenceItem:
    evidence_id: str
    text: str
    employer: str | None
    category: str
    similarity: float

    def render(self) -> str:
        return f"{self.text}" + (f" ({self.employer})" if self.employer else "")


@dataclass
class TailoringBrief:
    job_title: str
    company_name: str
    role_family: str | None
    lead_evidence: list[EvidenceItem] = field(default_factory=list)
    supporting_evidence: list[EvidenceItem] = field(default_factory=list)
    keywords_to_mirror: list[str] = field(default_factory=list)
    unsupported_requirements: list[str] = field(default_factory=list)
    preferred_gaps: list[str] = field(default_factory=list)
    qualification_statement: str = ""
    honesty_notes: list[str] = field(default_factory=list)

    @property
    def evidence_ids(self) -> list[str]:
        return [e.evidence_id for e in self.lead_evidence + self.supporting_evidence]

    def render_text(self) -> str:
        lines = [
            f"CV tailoring brief - {self.job_title} @ {self.company_name}",
            "=" * 72,
            "",
            f"Role family: {self.role_family or 'no confident match - review manually'}",
            "",
            "LEAD WITH (most relevant CV evidence for this posting):",
        ]
        lines += [f"  {i}. {item.render()}" for i, item in enumerate(self.lead_evidence, start=1)] or ["  (none)"]
        if self.supporting_evidence:
            lines += ["", "SUPPORTING EVIDENCE:"]
            lines += [f"  - {item.render()}" for item in self.supporting_evidence]
        if self.keywords_to_mirror:
            lines += [
                "",
                "MIRROR THIS POSTING'S VOCABULARY (only terms your CV already supports):",
                "  " + ", ".join(self.keywords_to_mirror),
            ]
        if self.unsupported_requirements:
            lines += ["", "REQUIREMENTS YOUR CV DOES NOT SUPPORT (do not claim these):"]
            lines += [f"  - {r}" for r in self.unsupported_requirements]
        if self.preferred_gaps:
            lines += ["", "PREFERRED-REQUIREMENT GAPS (worth addressing directly):"]
            lines += [f"  - {g}" for g in self.preferred_gaps]
        if self.qualification_statement:
            lines += ["", "QUALIFICATION WORDING (use exactly this framing):", f"  {self.qualification_statement}"]
        if self.honesty_notes:
            lines += ["", "NOTES:"] + [f"  - {n}" for n in self.honesty_notes]
        return "\n".join(lines)


@dataclass
class CoverLetterDraft:
    content: str
    evidence_ids: list[str]
    model_used: str = "deterministic"
    violations: list[ClaimViolation] = field(default_factory=list)


def _all_evidence_items() -> list[tuple[str, dict]]:
    evidence_map = load_cv_evidence_map().get("evidence_categories", {})
    return [(category, entry) for category, entries in evidence_map.items() for entry in entries]


def _rank_evidence(description_text: str, job_title: str, preferred_categories: list[str]) -> list[EvidenceItem]:
    """Rank CV evidence by similarity to this specific posting.

    Category membership alone is too coarse - a posting for an AI
    red-teaming role and one for AI curriculum design can share a role
    family while needing completely different bullets foregrounded.
    """
    index = get_role_family_index()
    job_vector = index.embedder.embed(f"{job_title}. {description_text or ''}")

    items: list[EvidenceItem] = []
    for category, entry in _all_evidence_items():
        text = entry.get("text", "")
        if not text:
            continue
        similarity = cosine_similarity(index.embedder.embed(text), job_vector)
        # Evidence in a category the matched role family maps to is
        # relevant by construction, so it gets a floor rather than being
        # dropped for using different words than the posting.
        if category in preferred_categories:
            similarity = max(similarity, MIN_EVIDENCE_SIMILARITY * 2)
        items.append(EvidenceItem(
            evidence_id=entry.get("id", f"{category}:{text[:24]}"),
            text=text,
            employer=entry.get("employer"),
            category=category,
            similarity=similarity,
        ))

    items.sort(key=lambda item: item.similarity, reverse=True)
    return [item for item in items if item.similarity >= MIN_EVIDENCE_SIMILARITY]


def _keywords_to_mirror(description_text: str, evidence_items: list[EvidenceItem], limit: int = 10) -> list[str]:
    """Terms the posting uses that Richard's evidence genuinely supports.

    The intersection matters: mirroring a posting's language helps with
    ATS keyword filters, but mirroring a term he has no evidence for is
    keyword stuffing that an interview would immediately expose.
    """
    index = get_role_family_index()
    evidence_vector_terms: set[str] = set()
    for item in evidence_items:
        evidence_vector_terms |= {
            feature.split(":", 1)[1]
            for feature in index.embedder.embed(item.text)
            if feature.startswith("w:")
        }

    job_terms = [
        (feature.split(":", 1)[1], weight)
        for feature, weight in index.embedder.embed(description_text or "").items()
        if feature.startswith("w:")
    ]
    job_terms.sort(key=lambda pair: pair[1], reverse=True)

    keywords: list[str] = []
    for term, _weight in job_terms:
        if len(term) > 3 and term in evidence_vector_terms and term not in keywords:
            keywords.append(term)
        if len(keywords) >= limit:
            break
    return keywords


def build_tailoring_brief(job_title: str, company_name: str, description_text: str) -> TailoringBrief:
    role_match = match_role_family(job_title, description_text)
    mismatches = find_mismatches(description_text, job_title=job_title)
    ranked = _rank_evidence(description_text, job_title, role_match.evidence_categories)

    lead = ranked[:3]
    supporting = ranked[3:MAX_EVIDENCE_ITEMS]

    honesty_notes = [
        "Every bullet above is quoted from config/cv_evidence_map.json, which is derived "
        "from the master CV. Nothing here is inferred or embellished.",
    ]
    if not role_match.role_family:
        honesty_notes.append(
            "No role family matched confidently - treat this brief as a starting point and "
            "check the posting yourself before applying."
        )
    if role_match.matched_via == "semantic_rescue":
        honesty_notes.append(
            "This posting matched on content rather than job title, so its title may not be "
            "the wording to mirror in your CV headline."
        )

    return TailoringBrief(
        job_title=job_title,
        company_name=company_name,
        role_family=role_match.role_family,
        lead_evidence=lead,
        supporting_evidence=supporting,
        keywords_to_mirror=_keywords_to_mirror(description_text, ranked[:MAX_EVIDENCE_ITEMS]),
        unsupported_requirements=mismatches.mandatory_mismatches,
        preferred_gaps=mismatches.preferred_gaps,
        qualification_statement=msc_status_sentence(),
        honesty_notes=honesty_notes,
    )


def build_cover_letter(brief: TailoringBrief) -> CoverLetterDraft:
    """Deterministic first draft, assembled only from evidence entries.

    Intentionally plain. This is a scaffold Richard edits, not a finished
    letter pretending to be one - and every sentence about his experience
    is a CV line, so editing it down can only make it more accurate.
    """
    profile = load_profile().get("candidate", {})
    name = profile.get("name", "Richard Best")
    positioning = profile.get("positioning", "")

    opening = (
        f"Dear Hiring Team,\n\n"
        f"I am writing to apply for the {brief.job_title} role at {brief.company_name}. "
        f"My background is in {positioning}, and the parts of this role I am strongest on are "
        f"set out below."
    )

    body_lines = ["\n"]
    for item in brief.lead_evidence:
        employer = f" at {item.employer}" if item.employer else ""
        body_lines.append(f"- {item.text.rstrip('.')}{employer}.")

    if brief.supporting_evidence:
        body_lines.append("")
        body_lines.append("Related experience:")
        for item in brief.supporting_evidence:
            body_lines.append(f"- {item.text.rstrip('.')}.")

    qualification = ""
    study_phrase = msc_study_phrase()
    if study_phrase:
        qualification = f"\n\nI am currently studying towards an {study_phrase}."

    gaps = ""
    if brief.unsupported_requirements:
        # Naming a gap plainly is more credible than papering over it,
        # and it is the only honest option when the CV genuinely lacks
        # something the posting asks for. The stored mismatch strings are
        # full sentences ("A completed master's degree is required - ..."),
        # so only the part before the explanation is quoted here.
        requirements = "; ".join(r.split(" - ")[0].rstrip(".") for r in brief.unsupported_requirements[:2])
        gaps = (
            f"\n\nOne note on fit. This posting states: {requirements}. "
            "I would rather say plainly that this is not part of my background than imply otherwise."
        )

    closing = f"\n\nI would welcome the chance to discuss the role.\n\nKind regards,\n{name}"

    content = opening + "\n".join(body_lines) + qualification + gaps + closing
    violations = validate_generated_text(content)
    return CoverLetterDraft(
        content=content,
        evidence_ids=brief.evidence_ids,
        model_used="deterministic",
        violations=violations,
    )


def unsupported_domain_reminder() -> list[str]:
    """Surfaced in the dashboard next to generated material so the
    "never claim these" list is visible at the moment of applying."""
    return unsupported_domains()
