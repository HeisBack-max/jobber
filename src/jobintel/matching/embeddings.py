"""Vector-space semantic retrieval for role matching (spec §32).

Why this exists: keyword and fuzzy-title matching both require the
vacancy to *use Richard's vocabulary*. A posting titled "Enterprise
Adoption Lead, Generative AI" describes the same work as "AI Enablement
Specialist" while sharing almost no tokens with it, and the fuzzy title
ratio alone can't tell that apart from "GTM Enablement - Expansion",
which shares a token but none of the meaning. Comparing whole documents
in a weighted vector space does distinguish them, because the *rest* of
the text is what disagrees.

What this is, precisely: sparse TF-IDF vectors over word unigrams, word
bigrams, and character 4-grams, compared by cosine similarity. It is a
lexical embedding, not a neural one - no model download, no external
API, no GPU, deterministic and offline, which keeps the whole app
runnable with nothing configured (spec §65 "must work with zero API
keys"). Character n-grams are what give it morphological reach:
"train"/"trainer"/"training"/"trainings" share n-grams, so the vacancy
does not have to inflect words the way the CV does.

If a neural sentence embedder is ever wanted, implement `TextEmbedder`
and pass it to `build_role_family_index()` - nothing else changes.

The index is built from the *profile corpus*: the role taxonomy in
config/roles.yaml plus the CV-grounded evidence text in
config/cv_evidence_map.json. That matters for honesty as much as for
quality: similarity is measured against what the CV actually says, so a
high semantic score is always traceable to real evidence rather than to
a general-purpose model's opinion of what the job sounds like.
"""

from __future__ import annotations

import functools
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field

from jobintel.settings import load_cv_evidence_map, load_roles, register_cache_clearer

CHAR_NGRAM_SIZE = 4

# A whole job description is the wrong unit to compare against a short
# role-family profile. Real ATS descriptions run 5-10 kB, most of which
# is company boilerplate, benefits, EEO statements and interview-process
# text, and every word of that dilutes the vector: cosine against the
# *full* document falls as the posting gets longer, so the most detailed
# postings - the ones most worth scoring well - score lowest. Measured
# over 650 real postings, whole-document similarity compressed every job
# into a 0.10-0.19 band with almost no separation between an AI-training
# role and an accounts-receivable one.
#
# Comparing the best *window* instead removes the length bias: a relevant
# posting has one strongly on-topic passage (its responsibilities or
# requirements section), and boilerplate windows simply lose.
WINDOW_WORDS = 90
WINDOW_STRIDE_WORDS = 45

# Tokens too generic to carry meaning in *any* job posting. Unlike the
# role_matcher's stopword list (which exists to stop one shared business
# word from anchoring a title match), this one only trims noise that
# would otherwise dominate the document vectors.
_STOPWORDS = {
    "the", "and", "or", "of", "a", "an", "for", "in", "on", "to", "with", "at", "by",
    "we", "you", "our", "your", "is", "are", "be", "will", "this", "that", "as", "from",
    "role", "job", "team", "work", "working", "experience", "years", "including",
    "ability", "strong", "excellent", "opportunity", "company", "candidate", "candidates",
}

_WORD_RE = re.compile(r"[a-z0-9+#]+")


def _words(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOPWORDS and len(w) > 1]


def _features(text: str) -> Counter:
    """Word unigrams + word bigrams + character n-grams."""
    words = _words(text)
    features: Counter = Counter()
    features.update(f"w:{w}" for w in words)
    features.update(f"b:{a}_{b}" for a, b in zip(words, words[1:], strict=False))

    condensed = " ".join(words)
    features.update(
        f"c:{condensed[i:i + CHAR_NGRAM_SIZE]}"
        for i in range(max(0, len(condensed) - CHAR_NGRAM_SIZE + 1))
    )
    return features


def text_windows(text: str, window_words: int = WINDOW_WORDS, stride: int = WINDOW_STRIDE_WORDS) -> list[str]:
    """Overlapping word windows over a document.

    Overlapping matters: a relevant passage split across a hard boundary
    would otherwise be halved and score like boilerplate.
    """
    words = (text or "").split()
    if not words:
        return []
    if len(words) <= window_words:
        return [" ".join(words)]
    return [
        " ".join(words[start:start + window_words])
        for start in range(0, max(1, len(words) - window_words + 1), stride)
    ]


class TextEmbedder(ABC):
    """Turns text into a sparse, L2-normalized vector (feature -> weight)."""

    @abstractmethod
    def embed(self, text: str) -> dict[str, float]: ...


class TfidfEmbedder(TextEmbedder):
    """TF-IDF fitted on a fixed corpus (the profile corpus, see module
    docstring). Unseen features fall back to the maximum IDF, so a rare
    term in an unseen vacancy is treated as informative rather than
    silently dropped."""

    def __init__(self, corpus: list[str]):
        self._document_count = max(1, len(corpus))
        document_frequency: Counter = Counter()
        for document in corpus:
            document_frequency.update(set(_features(document)))
        self._idf = {
            feature: math.log((self._document_count + 1) / (count + 1)) + 1.0
            for feature, count in document_frequency.items()
        }
        self._default_idf = math.log(self._document_count + 1) + 1.0

    def embed(self, text: str) -> dict[str, float]:
        counts = _features(text)
        if not counts:
            return {}
        vector = {
            feature: (1.0 + math.log(count)) * self._idf.get(feature, self._default_idf)
            for feature, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm == 0:
            return {}
        return {feature: value / norm for feature, value in vector.items()}


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Both inputs are already L2-normalized, so this is a dot product."""
    if not a or not b:
        return 0.0
    if len(b) < len(a):
        a, b = b, a
    return max(0.0, min(1.0, sum(weight * b.get(feature, 0.0) for feature, weight in a.items())))


@dataclass
class RoleFamilyIndex:
    """Embedded profile documents, one per role family."""

    embedder: TextEmbedder
    vectors: dict[str, dict[str, float]] = field(default_factory=dict)
    documents: dict[str, str] = field(default_factory=dict)

    def similarity(self, family_key: str, text_vector: dict[str, float]) -> float:
        return cosine_similarity(self.vectors.get(family_key, {}), text_vector)

    def windowed_similarity(self, family_key: str, text: str) -> float:
        """Best-window similarity: the length-robust measure (see
        WINDOW_WORDS above). Falls back to whole-text similarity for text
        shorter than one window."""
        family_vector = self.vectors.get(family_key, {})
        if not family_vector:
            return 0.0
        return max(
            (cosine_similarity(family_vector, self.embedder.embed(window)) for window in text_windows(text)),
            default=0.0,
        )

    def relative_standing(self, text: str, candidates: list[str]) -> dict[str, float]:
        """How strongly the text favours each candidate family, 0-1.

        Min-max normalized *across the candidates only*, which is the one
        thing this measure is actually good for. Absolute similarity is
        not: measured across 650 real postings, best-window cosine sits
        in a 0.10-0.19 band for relevant and irrelevant postings alike
        (an accounts-receivable role and an AI-training role are equally
        "similar" to the taxonomy in absolute terms, because a 15-document
        profile corpus cannot tell which English words are informative).
        What *is* reliable is the comparison between two families for the
        same text: the family whose vocabulary the posting genuinely
        shares wins by a clear margin.

        So this is a tie-breaker among families that already passed the
        title floor and anchor gate - never a standalone relevance score.
        """
        if not candidates:
            return {}
        windows = [self.embedder.embed(window) for window in text_windows(text)]
        sims = {
            family: max((cosine_similarity(self.vectors.get(family, {}), window) for window in windows), default=0.0)
            for family in candidates
        }
        top, bottom = max(sims.values()), min(sims.values())
        spread = top - bottom
        if spread <= 1e-9:
            # A single candidate, or an exact tie: nothing to discriminate.
            return dict.fromkeys(candidates, 1.0)
        return {family: (value - bottom) / spread for family, value in sims.items()}

    def rank_windowed(self, text: str, top_n: int = 5) -> list[tuple[str, float]]:
        windows = [self.embedder.embed(window) for window in text_windows(text)]
        scored = [
            (family, max((cosine_similarity(vector, window) for window in windows), default=0.0))
            for family, vector in self.vectors.items()
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_n]

    def rank(self, text: str, top_n: int = 5) -> list[tuple[str, float]]:
        """Most semantically similar role families for arbitrary text.

        This is the retrieval half of the feature: it works on a vacancy
        whose title matches nothing in the taxonomy, which is exactly the
        case keyword matching cannot serve.
        """
        vector = self.embedder.embed(text)
        scored = [(family, cosine_similarity(v, vector)) for family, v in self.vectors.items()]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_n]

    def explain(self, family_key: str, text: str, top_n: int = 6) -> list[str]:
        """The features contributing most to a similarity score.

        Every score this app shows has to be explainable (spec §65 "no
        unexplained magic scores"), and a cosine value on its own is not.
        """
        family_vector = self.vectors.get(family_key, {})
        text_vector = self.embedder.embed(text)
        contributions = [
            (feature, weight * text_vector.get(feature, 0.0))
            for feature, weight in family_vector.items()
            if feature.startswith(("w:", "b:")) and feature in text_vector
        ]
        contributions.sort(key=lambda item: item[1], reverse=True)
        return [feature.split(":", 1)[1].replace("_", " ") for feature, score in contributions[:top_n] if score > 0]


def _family_document(family_key: str, family: dict, evidence_by_category: dict[str, list[str]]) -> str:
    """One document per role family: its label, its example titles, and
    the CV evidence the family is mapped to."""
    parts = [family_key.replace("_", " "), family.get("label", "")]
    parts.extend(family.get("example_titles", []))
    for category in family.get("evidence_categories", []):
        parts.extend(evidence_by_category.get(category, []))
    return " . ".join(p for p in parts if p)


def _evidence_by_category() -> dict[str, list[str]]:
    evidence_map = load_cv_evidence_map().get("evidence_categories", {})
    return {
        category: [entry.get("text", "") for entry in entries]
        for category, entries in evidence_map.items()
    }


def build_role_family_index(embedder: TextEmbedder | None = None) -> RoleFamilyIndex:
    roles = load_roles().get("role_families", {})
    evidence = _evidence_by_category()
    documents = {key: _family_document(key, family, evidence) for key, family in roles.items()}

    embedder = embedder or TfidfEmbedder(list(documents.values()))
    return RoleFamilyIndex(
        embedder=embedder,
        vectors={key: embedder.embed(document) for key, document in documents.items()},
        documents=documents,
    )


@functools.lru_cache(maxsize=1)
def get_role_family_index() -> RoleFamilyIndex:
    """Cached: fitting the index reads two config files and embeds ~15
    documents, which is cheap but pointless to repeat per job in a run
    over several thousand postings."""
    return build_role_family_index()


register_cache_clearer(get_role_family_index.cache_clear)


@functools.lru_cache(maxsize=1)
def get_cv_vector() -> dict[str, float]:
    """The whole CV evidence map as one vector, for scoring a vacancy
    against Richard's evidence overall rather than per role family."""
    index = get_role_family_index()
    all_evidence = " . ".join(
        text for texts in _evidence_by_category().values() for text in texts
    )
    return index.embedder.embed(all_evidence)


register_cache_clearer(get_cv_vector.cache_clear)


def semantic_similarity_to_cv(text: str) -> float:
    """0-1 similarity between a vacancy and the CV evidence corpus,
    measured over the best window rather than the whole document."""
    index = get_role_family_index()
    cv_vector = get_cv_vector()
    return max(
        (cosine_similarity(cv_vector, index.embedder.embed(window)) for window in text_windows(text)),
        default=0.0,
    )
