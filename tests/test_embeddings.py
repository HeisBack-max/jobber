"""Semantic (vector-space) retrieval tests (spec §32).

The point of this layer is recall the keyword/fuzzy matcher structurally
cannot reach - a vacancy describing Richard's work in words the taxonomy
never lists - without reopening the false-positive class recorded in
IMPLEMENTATION_PLAN.md §7.3. Both halves are asserted here.
"""

from __future__ import annotations

from jobintel.matching.embeddings import (
    TfidfEmbedder,
    cosine_similarity,
    get_role_family_index,
    semantic_similarity_to_cv,
)
from jobintel.matching.role_matcher import match_role_family, semantic_prescore

AI_ADOPTION_POSTING = (
    "You will lead customer training programmes on generative AI adoption, "
    "build enablement curriculum, and deliver workshops to enterprise teams."
)
GTM_POSTING = (
    "ABOUT ACME AI. Acme AI is an AI research and product company. This role drives "
    "GTM enablement for our expansion sales teams, building playbooks and onboarding "
    "new account executives."
)


def test_cosine_similarity_bounds_and_identity():
    embedder = TfidfEmbedder(["ai training curriculum", "warehouse logistics scheduling"])
    a = embedder.embed("ai training curriculum")
    assert cosine_similarity(a, a) == 1.0 or abs(cosine_similarity(a, a) - 1.0) < 1e-9
    assert cosine_similarity(a, {}) == 0.0
    assert 0.0 <= cosine_similarity(a, embedder.embed("warehouse logistics scheduling")) <= 1.0


def test_character_ngrams_bridge_word_inflections():
    """"train"/"trainer"/"training" are different tokens to a keyword
    matcher; the character-n-gram channel is what makes them similar."""
    embedder = TfidfEmbedder(["deliver training sessions", "warehouse logistics"])
    similarity = cosine_similarity(
        embedder.embed("deliver training sessions"),
        embedder.embed("trainer delivering trainings"),
    )
    assert similarity > 0.15


def test_role_family_index_ranks_relevant_posting_above_noise():
    index = get_role_family_index()
    relevant = dict(index.rank(AI_ADOPTION_POSTING, top_n=3))
    noise = dict(index.rank("Manage indirect tax compliance across jurisdictions.", top_n=3))
    assert max(relevant.values()) > max(noise.values()) * 2


def test_semantic_prescore_separates_relevant_from_unrelated():
    """This number gates the paid LLM stage, so the gap between a real
    match and boilerplate noise has to be wide enough to threshold."""
    assert semantic_prescore("Enterprise Adoption Lead, Generative AI", AI_ADOPTION_POSTING) >= 0.45
    assert semantic_prescore("GTM Enablement - Expansion", GTM_POSTING) <= 0.30
    assert semantic_prescore("AV Engineer", "Install audio-visual equipment.") <= 0.30


def test_semantic_similarity_to_cv_is_grounded_in_evidence():
    assert semantic_similarity_to_cv("Red team LLMs, adversarial jailbreak testing, AI security training") > \
        semantic_similarity_to_cv("Operate a forklift in a distribution centre")


def test_semantic_channel_does_not_resurrect_known_false_positives():
    """The §7.3 regressions must stay dead with the semantic channel on:
    document similarity is allowed to widen recall, never to bypass the
    anchor-term gate."""
    assert match_role_family("GTM Enablement - Expansion", GTM_POSTING).role_family != "ai_training"
    assert match_role_family("AV Engineer", "Install and maintain audio-visual equipment.").role_family is None
    assert match_role_family(
        "International Indirect Tax, VAT/GST",
        "About Acme AI. Manage indirect tax compliance across multiple jurisdictions.",
    ).role_family is None


def test_match_result_exposes_explainable_semantic_terms():
    """A cosine value is not an explanation - the matcher has to be able
    to say which shared vocabulary drove it (spec §65)."""
    result = match_role_family(
        "AI Security Enablement Lead",
        "Lead LLM red-teaming and adversarial testing for enterprise AI security.",
    )
    assert result.role_family == "ai_security"
    assert result.semantic_score > 0
    assert result.semantic_terms
    assert any("red" in term or "adversarial" in term or "security" in term for term in result.semantic_terms)


def test_semantic_matching_can_be_disabled_in_config(monkeypatch):
    """Config, not code, decides whether this channel is on - and with it
    off the matcher must degrade to title+keyword scoring rather than
    breaking."""
    import jobintel.matching.role_matcher as rm

    original = rm.load_scoring()
    disabled = {**original, "semantic_matching": {**original["semantic_matching"], "enabled": False}}
    monkeypatch.setattr(rm, "load_scoring", lambda: disabled)

    result = match_role_family("Generative AI Trainer", AI_ADOPTION_POSTING)
    assert result.role_family is not None
    assert result.semantic_score == 0.0
    assert result.semantic_terms == []
    # With the semantic gate off, nothing should be blocked on that signal.
    assert semantic_prescore("anything", "anything") == 1.0


def test_generic_org_noun_in_keywords_does_not_hijack_a_training_role(monkeypatch):
    """Regression: "team" was extracted as a keyword from ai_security's
    "AI Red Team" example titles and then matched the phrase "enterprise
    teams" in a pure training posting's boilerplate - enough to hand a
    Generative AI Trainer role to the AI-security family. Same class of
    bug as "enablement" in IMPLEMENTATION_PLAN.md §7.3, one level down in
    the keyword channel. Must hold with the semantic channel both on and
    off, since keyword noise is not the semantic layer's job to clean up.
    """
    import jobintel.matching.role_matcher as rm

    assert match_role_family("Generative AI Trainer", AI_ADOPTION_POSTING).role_family == "ai_training"

    original = rm.load_scoring()
    disabled = {**original, "semantic_matching": {**original["semantic_matching"], "enabled": False}}
    monkeypatch.setattr(rm, "load_scoring", lambda: disabled)
    assert match_role_family("Generative AI Trainer", AI_ADOPTION_POSTING).role_family == "ai_training"


def test_semantic_channel_discriminates_between_sibling_families():
    """Corroboration, not decoration: for a posting about curriculum and
    workshops, document similarity to the AI-training family must clearly
    exceed similarity to its AI-security sibling, so the channel actually
    carries signal when title and keyword scores are close."""
    index = get_role_family_index()
    vector = index.embedder.embed(f"Generative AI Trainer. {AI_ADOPTION_POSTING}")
    assert index.similarity("ai_training", vector) > index.similarity("ai_security", vector) * 1.4


def test_semantic_rescue_matches_a_posting_that_avoids_taxonomy_vocabulary():
    """The recall half: a real AI-enablement role whose title shares
    almost nothing with the taxonomy must still be found, and the result
    must say it was matched on content rather than title."""
    result = match_role_family(
        "Customer Success Architect - AI Adoption Programmes",
        "Own the end-to-end AI adoption journey for enterprise accounts: run onboarding "
        "workshops, build learning paths and curriculum for customer teams, and coach "
        "users on prompt engineering and generative AI best practice.",
    )
    assert result.role_family is not None
    assert result.semantic_score > 0.3
