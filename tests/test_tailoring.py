"""CV tailoring / cover-letter tests (spec §27/§28/§39).

The tests that matter most here are the negative ones. A ranking bug
shows Richard an irrelevant job; a fabrication bug puts a false claim in
a document he sends to an employer under his own name, so every
anti-fabrication rule gets an explicit test, including the case where an
LLM rewrite tries to introduce one.
"""

from __future__ import annotations

import asyncio

import pytest

from jobintel.tailoring.generator import build_cover_letter, build_tailoring_brief
from jobintel.tailoring.guardrails import msc_study_phrase, unsupported_domains, validate_generated_text
from jobintel.tailoring.service import COVER_LETTER, CV_TAILORING_BRIEF, generate_materials

AI_SECURITY_POSTING = (
    "We are hiring an AI Security Trainer to deliver enterprise AI security and red-teaming "
    "training. Remote worldwide. You will design curriculum, run workshops on adversarial LLM "
    "testing and prompt injection, and support customer enablement."
)
CURRICULUM_POSTING = (
    "AI Curriculum Developer. Build instructional design artefacts and adult-learning "
    "curriculum for a generative AI training programme delivered to enterprise learners."
)


def test_brief_foregrounds_evidence_relevant_to_this_posting():
    """Two postings in overlapping role families must not produce the
    same brief - the whole point is per-posting ranking, not CV order."""
    security = build_tailoring_brief("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING)
    curriculum = build_tailoring_brief("AI Curriculum Developer", "Acme AI", CURRICULUM_POSTING)

    assert security.lead_evidence
    assert curriculum.lead_evidence
    assert [e.evidence_id for e in security.lead_evidence] != [e.evidence_id for e in curriculum.lead_evidence]

    security_text = " ".join(e.text.lower() for e in security.lead_evidence)
    curriculum_text = " ".join(e.text.lower() for e in curriculum.lead_evidence)
    assert "red-team" in security_text or "red team" in security_text or "llm" in security_text
    assert "curriculum" in curriculum_text or "instructional" in curriculum_text or "learning" in curriculum_text


def test_every_cited_claim_is_traceable_to_the_cv_evidence_map():
    """The auditability guarantee: each brief records evidence ids, and
    each id must exist in config/cv_evidence_map.json."""
    from jobintel.settings import load_cv_evidence_map

    known_ids = {
        entry.get("id")
        for entries in load_cv_evidence_map()["evidence_categories"].values()
        for entry in entries
    }
    brief = build_tailoring_brief("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING)
    assert brief.evidence_ids
    for evidence_id in brief.evidence_ids:
        assert evidence_id in known_ids


def test_keywords_to_mirror_never_include_unsupported_terms():
    """Mirroring a posting's vocabulary is only safe for terms the CV
    actually supports - anything else is keyword stuffing that would fall
    apart in an interview."""
    posting = AI_SECURITY_POSTING + " Requires Kubernetes, Terraform and Rust."
    brief = build_tailoring_brief("AI Security Trainer", "Acme AI", posting)
    assert "kubernetes" not in brief.keywords_to_mirror
    assert "terraform" not in brief.keywords_to_mirror
    assert "rust" not in brief.keywords_to_mirror


def test_unsupported_requirements_are_surfaced_not_hidden():
    posting = AI_SECURITY_POSTING + " A completed master's degree is required."
    brief = build_tailoring_brief("AI Security Trainer", "Acme AI", posting)
    assert any("master" in r.lower() for r in brief.unsupported_requirements)

    letter = build_cover_letter(brief)
    # The letter must name the gap rather than quietly omitting it.
    assert "master" in letter.content.lower()
    assert not letter.violations


def test_generated_cover_letter_passes_every_guardrail():
    brief = build_tailoring_brief("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING)
    letter = build_cover_letter(brief)
    assert letter.violations == []
    assert "Richard Best" in letter.content


def test_msc_is_never_presented_as_completed():
    brief = build_tailoring_brief("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING)
    letter = build_cover_letter(brief).content.lower()
    assert "in progress" in msc_study_phrase().lower()
    assert "studying towards" in letter
    for phrase in ("completed my msc", "my msc in", "holds an msc", "earned my master"):
        assert phrase not in letter


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("I completed my MSc in Data Analytics last year.", "msc_must_be_in_progress"),
        ("I hold a Master's degree in Data Analytics.", "msc_must_be_in_progress"),
        ("I am fluent in Arabic after working in Saudi Arabia.", "no_unevidenced_languages"),
        ("Conversational Russian from my time in Kazakhstan.", "no_unevidenced_languages"),
        ("I am authorized to work in the United States.", "no_us_work_authorization_claim"),
        ("I hold an active security clearance.", "no_security_clearance_claim"),
        ("My PhD research focused on model safety.", "no_phd_claim"),
        ("I have eight years of production software engineering behind me.", "no_production_engineering_claim"),
    ],
)
def test_guardrails_catch_each_fabrication_class(text, rule):
    violations = validate_generated_text(text)
    assert rule in {v.rule for v in violations}, f"{rule} not flagged for {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "I am currently studying towards an MSc Data Analytics at University of Cumbria (2024 - 2027, in progress).",
        "My MSc Data Analytics is in progress and expected in 2027.",
        "I delivered training in Saudi Arabia and Kazakhstan.",
        "I have delivered security awareness training to teams handling classified material.",
    ],
)
def test_guardrails_do_not_flag_honest_phrasing(text):
    """Over-blocking would be its own failure: a rule that fires on "I am
    studying towards an MSc" would force the generator to hide a real,
    relevant qualification."""
    assert validate_generated_text(text) == []


def test_unsupported_domains_come_from_the_evidence_map():
    domains = unsupported_domains()
    assert any("master" in d.lower() for d in domains)
    assert any("language" in d.lower() for d in domains)


def test_llm_rewrite_that_fabricates_is_rejected_and_deterministic_draft_kept(monkeypatch):
    """Fail-closed: if the model upgrades the in-progress MSc, the
    rewrite is discarded rather than stored."""
    fabricated = (
        "Dear Hiring Team,\n\nWith my completed MSc in Data Analytics and fluent Arabic, I am "
        "the ideal candidate.\n\nKind regards,\nRichard Best"
    )

    async def fake_rewrite(brief, draft, description_text):
        return fabricated, "anthropic"

    monkeypatch.setattr("jobintel.tailoring.service._llm_rewrite", fake_rewrite)
    result = asyncio.run(generate_materials("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING, use_llm=True))

    assert result.rewrite_rejected is True
    assert result.cover_letter.content != fabricated
    assert result.cover_letter.model_used == "deterministic"
    assert any("msc_must_be_in_progress" in reason for reason in result.rejection_reasons)
    assert "fluent Arabic" not in result.cover_letter.content


def test_clean_llm_rewrite_is_accepted(monkeypatch):
    clean = (
        "Dear Hiring Team,\n\nI led red-teaming exercises on a proprietary enterprise LLM at "
        "Soteria, testing jailbreak resilience.\n\nKind regards,\nRichard Best"
    )

    async def fake_rewrite(brief, draft, description_text):
        return clean, "anthropic"

    monkeypatch.setattr("jobintel.tailoring.service._llm_rewrite", fake_rewrite)
    result = asyncio.run(generate_materials("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING, use_llm=True))

    assert result.rewrite_rejected is False
    assert result.cover_letter.content == clean
    assert result.cover_letter.model_used == "anthropic"


def test_no_api_key_means_no_llm_call_and_a_usable_draft(monkeypatch):
    """The app must be fully functional with zero API keys configured."""
    from jobintel import settings as settings_module

    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = asyncio.run(generate_materials("AI Security Trainer", "Acme AI", AI_SECURITY_POSTING, use_llm=True))
    assert result.cover_letter.model_used == "deterministic"
    assert result.cover_letter.content
    assert result.rewrite_rejected is False
    settings_module.get_settings.cache_clear()


def test_materials_are_persisted_with_their_evidence_ids(temp_db):
    from jobintel.db.models import ApplicationMaterial, Job
    from jobintel.tailoring.service import generate_and_store_materials

    with temp_db.session_scope() as session:
        job = Job(
            source="greenhouse", source_job_id="1", source_url="u", canonical_url="u",
            company_name="Acme AI", job_title="AI Security Trainer",
            normalized_job_title="ai security trainer",
            job_description_clean=AI_SECURITY_POSTING, content_hash="hash-1",
        )
        session.add(job)
        session.flush()
        job_id = job.id

    asyncio.run(generate_and_store_materials(job_id, use_llm=False))

    with temp_db.session_scope() as session:
        materials = session.query(ApplicationMaterial).filter_by(job_id=job_id).all()
        kinds = {m.kind for m in materials}
        assert kinds == {CV_TAILORING_BRIEF, COVER_LETTER}
        for material in materials:
            assert material.evidence_ids
            assert material.content
