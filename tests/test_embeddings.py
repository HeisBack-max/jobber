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
# Representative of what a real ATS posting is mostly made of - the text
# that dilutes whole-document similarity.
_BOILERPLATE = (
    "About the company: we are a fast-growing enterprise technology company working with "
    "customers around the world. Our team values collaboration, ownership and a high bar for "
    "technical excellence. What we offer: competitive compensation, equity, comprehensive "
    "health, dental and vision cover, generous paid time off, a home-office budget and an "
    "annual learning and development allowance. Interview process: an introductory conversation "
    "with our recruiting team, a role-specific interview with the hiring manager, a practical "
    "exercise, and a final panel with cross-functional stakeholders. We are an equal opportunity "
    "employer and value diversity at our company. We do not discriminate on the basis of race, "
    "religion, colour, national origin, gender, sexual orientation, age, marital status, veteran "
    "status or disability status. We are committed to providing reasonable accommodations "
    "throughout the interview process and in the workplace. All employees are expected to work "
    "collaboratively with colleagues across engineering, product, sales and customer teams. "
) * 3

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
    # The Stage 2 pre-score is the combined match confidence, so it keeps
    # working (on title + keywords alone) with the semantic channel off,
    # and still separates a real match from an unrelated posting.
    assert semantic_prescore("Generative AI Trainer", AI_ADOPTION_POSTING) > 0.4
    assert semantic_prescore("Senior Accountant", "Own month-end close and reconciliations.") == 0.0


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


def test_semantic_prescore_is_a_real_cost_gate():
    """The Stage 2 gate has to actually stop postings, or it is a cost
    control in name only.

    It deliberately uses the combined match confidence rather than raw
    document similarity: measured over 650 real ATS postings, raw
    best-window cosine sat in a 0.10-0.19 band for relevant and
    irrelevant postings alike (an accounts-receivable role scored like an
    AI-training role), and 97% of postings cleared the configured 0.35
    threshold on it. The combined score matched 221 of those 650 and gave
    the rest exactly 0.
    """
    assert semantic_prescore("AI Security Enablement Lead", "Lead LLM red-teaming and adversarial testing.") >= 0.5
    assert semantic_prescore("Senior Accountant", "Own month-end close, reconciliations and the ledger.") == 0.0
    assert semantic_prescore("Hardware Lab Manager", "Oversee cabling crews, electricians and lab equipment.") == 0.0


def test_absolute_document_similarity_is_not_used_as_a_relevance_score():
    """Guards the calibration decision above against being quietly undone.

    On a short, keyword-dense string absolute similarity looks like it
    works. On a real 5-10 kB ATS posting it does not: the company
    boilerplate every posting shares ("customer", "enterprise",
    "technical", "training", benefits, EEO, interview process) fills the
    windows and pulls relevant and irrelevant postings into the same
    band. That is why nothing gates on this number - it is a tie-breaker
    between families for one posting only.
    """
    index = get_role_family_index()

    relevant = f"Deliver AI security training and run red-team exercises for enterprise customers. {_BOILERPLATE}"
    irrelevant = f"Own month-end close, reconciliations, accounts payable and the general ledger. {_BOILERPLATE}"

    relevant_score = max(v for _, v in index.rank_windowed(relevant, top_n=3))
    irrelevant_score = max(v for _, v in index.rank_windowed(irrelevant, top_n=3))

    # Both land in the same narrow band once real boilerplate is present.
    assert abs(relevant_score - irrelevant_score) < 0.12

    # The matcher still gets it right, because it gates on the title and
    # anchor terms first and only then asks the semantic index.
    assert match_role_family("AI Security Trainer", relevant).role_family is not None
    assert match_role_family("Senior Accountant", irrelevant).role_family is None


def test_relative_standing_only_compares_candidates_it_is_given():
    """The measure is a tie-breaker, not a classifier: asked to rank an
    unrelated posting against one family, it must not be interpretable as
    "this posting is relevant" - which is why the matcher never calls it
    before the title floor and anchor gate have run."""
    index = get_role_family_index()
    standing = index.relative_standing(
        "Own month-end close and reconciliations.", ["ai_training", "cybersecurity_training"]
    )
    assert set(standing) == {"ai_training", "cybersecurity_training"}
    assert max(standing.values()) == 1.0  # something is always "top" - meaningless alone
    assert match_role_family("Senior Accountant", "Own month-end close and reconciliations.").role_family is None


def test_single_candidate_gets_no_free_semantic_bonus():
    """With one plausible family there is nothing to compare against, so
    the semantic weight is redistributed rather than granted. Handing out
    a constant bonus is a disguised threshold change - and it let "Senior
    Accountant" clear the match floor during calibration."""
    result = match_role_family("Generative AI Trainer", AI_ADOPTION_POSTING)
    if result.semantic_score == 0.0:
        # Single-candidate path: score must be explainable from title and
        # keywords alone.
        assert result.combined_score <= result.title_score + 0.01
