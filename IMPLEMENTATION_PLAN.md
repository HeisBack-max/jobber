# Implementation Plan — Remote Job Intelligence

## 1. Contradictions / unresolved assumptions found before coding

- **Contact phone country code.** The CV lists a +855 (Cambodia) phone
  number under a "Burton upon Trent, UK" address line. This has no
  bearing on scoring/eligibility logic (which is about *opportunity*
  location requirements, not Richard's current physical location) so no
  code depends on it, but it is noted here rather than silently
  resolved. `config/profile.yaml` does not hard-code a home country for
  Richard for this reason.
- **MSc completion date.** CV states "2024 - 2027: In progress; expected
  2027." Every reference to this qualification in `cv_evidence_map.json`
  and any future explanation text must say "in progress" - never
  "completed" or "MSc". Enforced by keeping `status: IN_PROGRESS` as
  structured data rather than free text that could be paraphrased away.
- **No languages other than English evidenced.** The CV does not state
  fluency in any language besides English despite extensive work in
  non-English-speaking countries. `explicit_non_evidence` in the CV
  evidence map records this explicitly so the matcher never infers, e.g.,
  Arabic or Russian proficiency from "delivered training in Saudi
  Arabia/Kazakhstan."
- **OpenAI/Google/Microsoft/Amazon/Meta do not run public Greenhouse/
  Lever/Ashby boards.** *(Partly wrong - corrected 2026-08-22, see §8.)* The spec assumes these are checked "deliberately"
  but does not mandate a specific mechanism. Resolution: they are listed
  in `config/strategic_companies.yaml` with `verification_status:
  NO_PUBLIC_ATS` or `UNVERIFIED` and a `notes` field explaining what
  collector type would be needed (career-site HTML or search discovery -
  both future work, tracked in §6 below). Building deliberately-fake
  "coverage" for these via a brittle scraper would violate §65 ("NO
  brittle monolithic scraping script"), so the MVP is honest that this
  channel is a framework + registry today, not a working collector.
  `discovery/strategic_watch.py` still surfaces this gap to the
  dashboard/source-health view rather than hiding it.
- **Outlier AI (and comparable gig marketplaces) require authenticated
  login.** *(Still true; the gig channel was closed a different way - see §8.)* No public, unauthenticated job-listing API exists. Building a
  scraper against an authenticated session would risk ToS violation and
  credential handling outside this app's threat model. Resolution: the
  `gigs/` package defines the `GigSource` interface, the canonical
  `GigPosting` schema, and the gig scoring model in full, but ships zero
  working Outlier collector. This is flagged, not silently stubbed - see
  `gigs/outlier.py` docstring and the dashboard's source-health panel.
- **"Verify Greenhouse/Lever/Ashby mechanisms" vs. sandboxed egress.**
  `developers.greenhouse.io` and `developers.ashbyhq.com` were blocked by
  this environment's egress proxy during verification. Endpoints were
  cross-checked via the public `grnhse/greenhouse-api-docs` GitHub mirror
  and indexed documentation snippets instead of the primary docs pages.
  See ARCHITECTURE.md §6 for what was and wasn't independently
  confirmed, and `scripts/verify_boards.py` for the runtime check that
  catches a stale/wrong token before it silently reads as "no jobs."

None of the above blocks proceeding - all are resolved with documented,
conservative defaults per the spec's instruction to make sensible calls
and continue rather than stalling on routine decisions.

## 2. MVP scope actually implemented in this pass

Built and tested:

- Configuration system (`config/*.yaml`, `cv_evidence_map.json`)
- Database schema + Alembic migration (SQLite)
- Greenhouse, Lever, Ashby collector adapters (real HTTP, real schemas)
- Normalization to the canonical opportunity schema
- Deterministic geography/remote-classification engine + eligibility
- Deduplication (content hash + fuzzy match) and repost detection
- Semantic + negative matching against role taxonomy and CV evidence
- Career scoring + gig scoring engines, fully explainable
- `JobEvaluator` abstraction with a real Anthropic-backed implementation,
  Pydantic-validated structured output, retry-on-invalid, cost tracking,
  and a `NullEvaluator` that is used automatically when no API key is
  configured (jobs simply stop at semantic-pre-score rather than getting
  a fabricated LLM result)
- Prompt-injection defenses + test
- Application tracking + feedback tables
- Streamlit dashboard with the 7 required feeds, filters, and cards
- Daily digest generator
- Structured logging + source health tracking
- CLI (`jobintel collect|evaluate|digest|run|dashboard`)
- pytest suite covering the required fixture scenarios

Explicitly deferred at MVP time (documented, not silently dropped - see
spec §61 "Future Phases" for precedent):

- Live collectors for companies without a public Greenhouse/Lever/Ashby
  board (OpenAI, Google, Microsoft, Amazon, Meta, etc.)
- A working Outlier AI (or similar) gig collector.
- Embedding-based semantic retrieval.
- Notification adapters beyond the interface.
- CV tailoring / cover-letter generation.

**All five were taken off the deferred list in the 2026-08-22 pass -
four completed, one closed a different way. See §8 for what was built,
what was verified live, and the two things that remain genuinely
uncollectable.**

## 3. Configuration model

See `config/profile.yaml` (candidate + preferences + geography rules),
`config/roles.yaml` (role taxonomy + negative-matching signals),
`config/sources.yaml` (board registry actually polled, plus muted
shipped-but-unverified entries), `config/strategic_companies.yaml` (full
strategic watchlist incl. companies without a working collector yet),
`config/search_queries.yaml` (search-discovery query families, backend
toggles, and career-site keyword terms), `config/manual_gigs.yaml` (gigs
entered by hand for platforms that publish no API),
`config/scoring.yaml` (every scoring weight/threshold, including the
`semantic_matching` channel weights), `config/cv_evidence_map.json`
(CV-grounded evidence, factual authority per the spec's precedence rule).

## 4. Database schema (implemented in `alembic/versions/0001_initial.py`)

- `companies` — registry entry: name, ats, board_token, career_url,
  collection_status, strategic_themes (JSON), verification_status,
  last_successful_check, last_changed, source_health
- `jobs` — canonical opportunity per spec §33 (full column list matches
  the spec's schema field-for-field)
- `job_sources` — provenance: one job → many discovery sources, each with
  its own source_url/source_type/first_seen_at/quality_rank
- `job_analysis` — per spec §34: all component scores, overall_score,
  confidence_score, recommendation, mandatory_mismatches (JSON),
  preferred_gaps (JSON), strengths/concerns (JSON), reasoning_summary,
  model_used, prompt_version, evaluated_at
- `gigs` — gig/project-specific fields (hourly rate, duration, weekly
  hours) + `gig_analysis` for the gig_quality_score breakdown *(the
  `gig_analysis` table was promised here at MVP time but never created;
  added in migration 0002 - see §8.4)*
- `application_materials` — generated CV-tailoring briefs and cover
  letters, with the cv_evidence_map ids each cites so any claim in a
  generated document stays auditable back to a line of the real CV
  (migration 0002)
- `notification_log` — one row per delivery attempt per channel, which is
  what makes "alert once per job" true across runs (migration 0002)
- `application_status` — status history with timestamps + notes +
  recruiter contact fields
- `feedback` — 👍/👌/👎/🚫 + reason, used for transparent ranking
  adjustment (not opaque retraining, per spec §38)
- `source_health` — per-run collection stats per source
- `llm_usage` — tokens/cost/provider/model per evaluation call, for
  `cost_control.daily_llm_budget_usd` enforcement

## 5. Development order followed

Milestones 1→5 implemented fully and tested. Milestone 6 was implemented
as registry + framework at MVP time and completed in the 2026-08-22 pass
(see §8): 75 verified boards, four additional ATS adapters, three
career-site collectors, and aggregator-backed search discovery.
Milestone 7 (dashboard) implemented against the real schema. Milestone 8
(automation) implemented as `scripts/daily_run.py` + APScheduler wiring;
milestone 9 (tests/README) completed alongside each milestone rather than
saved for the end, since the spec requires tests to verify decisions, not
just exercise code paths.

## 6. Genuine technical risks

1. **Board token drift.** Greenhouse/Lever/Ashby board tokens for
   strategic companies change or get renamed. Mitigated by
   `scripts/verify_boards.py` and `source_health` tracking rather than
   assuming a token is permanently valid.
2. **LLM structured-output drift.** Anthropic model updates can change
   how reliably the model returns valid JSON. Mitigated by Pydantic
   validation + bounded retries + logging (never persisting invalid
   output).
3. **False "worldwide remote" classification.** The single highest-risk
   correctness bug for this product would be marking a US-only or
   Thailand-only role as eligible. Mitigated by defaulting to `UNCLEAR`
   (manual review) rather than `YES` whenever deterministic extraction is
   not confident, and by the large geography test suite.
4. **No public ATS for the highest-profile strategic employers.** OpenAI/
   Google/Microsoft/Amazon/Meta discovery is currently registry-only.
   This is the most likely area for Richard to notice "missing"
   opportunities; it's surfaced honestly in source health rather than
   papered over.

## 7. Bugs found and fixed against real collected data (2026-08-14)

The first live run against real Greenhouse/Lever/Ashby traffic (once the
sandbox's network policy allowlisted the three ATS hosts) surfaced two
classes of bug that the mocked/fixture-based test suite had not caught,
because the fixtures were hand-written with realistic-looking but
synthetic descriptions - they never exercised the actual shape of a real
`fetch_details()` payload.

1. **Every collected job had an empty description.** `JobSource.fetch_details()`'s
   default implementation (`jobintel/collectors/base.py`) never extracted
   `description_html`/`description_text` from the raw payload - it just
   echoed `raw_payload` back. None of the three adapters overrode it, so
   `job_description_clean` was `""` for all 1,424 jobs on the first real
   run, which meant the geography classifier had almost nothing to work
   with beyond the structured `location_raw` field (e.g. "Sydney,
   Australia" alone, with no "remote worldwide" language to key off) -
   1,423 of 1,424 jobs came back `UNCLEAR`. Fixed by adding real
   `fetch_details()` overrides to all three collectors (the list
   responses already contain the full description - no second request
   needed) and by unescaping Greenhouse's doubly-HTML-entity-escaped
   `content` field before parsing. Regression tests added in
   `tests/test_collectors.py` and `tests/test_clean.py`.
2. **`config/sources.yaml` had Cohere on the wrong ATS entirely.**
   `greenhouse:cohere` 404'd - that token belongs to an unrelated
   healthcare company ("Cohere Health"). The AI company Cohere is on
   Ashby (`ashby:cohere`, confirmed live). Fixed in both
   `config/sources.yaml` and `config/strategic_companies.yaml`.
3. **Role-family matching produced false positives on generic business
   titles.** Once real descriptions were flowing, generic titles sharing
   a single word with an example title (most commonly "Enablement" -
   present in `ai_training`'s, `technical_training`'s, *and*
   `customer_education`'s example titles) fuzzy-matched across totally
   unrelated roles: "GTM Enablement - Expansion" scored as a Tier-A
   `ai_training` STRONG_APPLY; "International Indirect Tax, VAT/GST"
   matched `technical_instructional_design`; "AV Engineer" matched
   `prompt_engineering` purely off the shared word "Engineer". Fixed in
   `jobintel/matching/role_matcher.py` with three changes: (a) a hard
   minimum title-fuzzy-ratio floor before a family is even a candidate,
   (b) stripping generic stopwords from *both* the job title and the
   example titles before fuzzy comparison (not just from keyword
   extraction, which is what let "enablement" alone drive a high ratio),
   and (c) a literal-anchor-term requirement (no fuzzy-ratio fallback) for
   the AI/cybersecurity-specific families, plus a tie-break penalty so
   the catch-all `ai_training` family doesn't out-rank a more specific
   sibling family (e.g. `ai_security`) on a coincidental shared word.
   Regression tests added in `tests/test_matching_scoring.py` for each
   specific failure observed.

This remains an inherently imprecise, keyword/fuzzy-matching-based MVP
approach (per §2's explicit scope decision to defer embedding-based
semantic retrieval) - it is now dramatically more conservative about
false positives than before, but borderline Tier B/C matches on
business-adjacent titles at AI companies (e.g. a marketing or technical
support role) will still sometimes surface for human review rather than
being filtered out entirely. That is an intentional trade-off consistent
with spec §51's guidance to distinguish `MANDATORY_MISMATCH` from
softer, reviewable fit - not a bug to keep chasing indefinitely with more
regex special-casing. The Stage 3 LLM refinement pass (which requires
`ANTHROPIC_API_KEY`, not configured in this session) is the intended
mechanism for catching this class of residual imprecision going forward.

## 8. Completing the deferred work (2026-08-22)

Every item on §2's deferred list was taken off it in this pass. Four were
built; the fifth (Outlier AI) is still impossible as originally framed
and was closed a different way. Two things remain genuinely uncollectable
and are called out at the end rather than papered over.

### 8.1 Employers without a public Greenhouse/Lever/Ashby board

The MVP's assumption here was **partly wrong, and the wrong part was the
expensive one**. Probing candidate board tokens against the three public
ATS APIs and then identity-checking every hit found that most of the
strategic watchlist *does* run a collectable public board - including
OpenAI, which §1 had recorded as "no confirmed public board; careers site
appears to run a custom ATS". OpenAI publishes 754 postings through
Ashby; the board simply is not linked from the careers page navigation.

`config/sources.yaml` went from 6 boards to **75 verified, identity-checked
boards**, all confirmed live through the real adapters (not curl) by
`jobintel verify-boards`:

- frontier AI labs (OpenAI, Anthropic, xAI, Perplexity, Mistral, Cohere,
  Together AI, Cerebras, Sierra, Harvey, Cursor, Replit, LangChain, ...)
- the strategic watchlist's European/regional targets (Helsing, DeepL,
  Synthesia, Wayve, Aleph Alpha, Quantexa, Isomorphic Labs, Owkin, n8n,
  Sarvam, FuriosaAI, Palantir, Snowflake, ...)
- AI-data / model-training marketplaces (Mercor, Turing, Toloka, Appen,
  Invisible, Snorkel, Labelbox, Prolific) - which also turned out to be
  the answer to the gig problem, see §8.4
- cybersecurity employers that hire trainers (KnowBe4, Immersive Labs,
  HackerOne, Bugcrowd, Synack, Sophos, Recorded Future, Dragos)
- learning platforms (Coursera, Udemy, DataCamp, Multiverse, Skillsoft,
  Docebo, 360Learning)
- remote-first technology employers (GitLab, Cloudflare, Docker, Zapier,
  Supabase, Vercel, Mozilla, Remote.com, Handshake)

For the employers that genuinely run their own ATS, four new adapters and
three career-site collectors were written: `workday`, `smartrecruiters`,
`workable`, `recruitee`, and `careersite_microsoft` / `careersite_amazon`
/ `careersite_google`. These are **implemented but not verified live**:
the environment they were written in blocks those hosts at the
network-policy layer. Rather than claim coverage that has never answered
a request, their `config/sources.yaml` entries ship `collection_status:
muted` - the adapter exists, `jobintel verify-boards` checks it, and it
starts being polled only when a real 200 promotes it. That distinction is
now a first-class registry concept rather than a comment.

Identity-checking is part of verification now, not an afterthought. Three
tokens resolved to entirely different companies than their names suggest:
`greenhouse:figure` (not Figure AI), `ashby:runway` (a business-planning
startup, not RunwayML), and the already-known `greenhouse:cohere`
(Cohere Health). Each was caught by reading a sample posting.

### 8.2 Search discovery

`discovery/search.py` implements aggregator-backed discovery over the
query families in `config/search_queries.yaml` (Remotive and RemoteOK,
both public documented APIs). Anything found this way is recorded as
`source_type=aggregator` with a worse `quality_rank`, which means an
employer's own posting always overwrites the aggregator copy and an
aggregator-only job takes the `aggregator_only_source` confidence
deduction - provenance that previously existed in the schema but was
hard-coded to `official_ats` everywhere.

Both backends ship **disabled** for the same reason the career-site
collectors ship muted: unreachable from here, therefore unproven.
`jobintel verify-search` is the check that promotes them.

### 8.3 Vector-space semantic retrieval

`matching/embeddings.py` adds sparse TF-IDF vectors over word unigrams,
word bigrams and character 4-grams, fitted on the *profile corpus* (the
role taxonomy plus the CV evidence map). It is a lexical embedding, not a
neural one - no model download, no external API, deterministic and
offline, so the app still runs with zero API keys configured. A neural
embedder can be dropped in behind the `TextEmbedder` interface without
touching anything else.

**What the measurement changed.** The first cut of this used absolute
document similarity as a relevance score, normalized against a fixed
reference, with a "semantic rescue" path that let strong content
similarity admit a family whose title did not clear the floor. Measuring
it against 650 real postings showed that design was wrong in two ways:

- Absolute similarity barely discriminates. Full-length ATS postings
  (median 7.4 kB here) all land in a 0.10-0.19 band, relevant or not: an
  accounts-receivable role at an AI company scores like an AI-training
  role, because the boilerplate every posting shares - benefits, EEO
  text, interview process, "customer", "enterprise", "technical" -
  dominates the vector. Windowing the document to its best passage
  narrowed the gap rather than widening it. A 15-document profile corpus
  simply cannot learn which English words are informative.
- Consequently the rescue threshold was unreachable in practice, and the
  Stage 2 gate that depended on the same number admitted 97% of postings
  while ranking generic customer-success roles highest. Both looked like
  working controls and were not.

So the design changed to match what the measure is actually good at:

- **Two passes.** Title similarity and anchor terms decide which families
  are plausible; the semantic index then ranks *only those candidates*
  against each other, min-max normalized. Comparing two families for one
  posting is reliable in a way that scoring one posting in the abstract
  is not.
- **No rescue path.** It is deleted rather than left in with a threshold
  tuned to never fire. A rescue built on a measure that cannot separate
  relevant from irrelevant text would either do nothing or do harm, and
  the honest answer is to say so. Recall for "same job, different words"
  therefore still depends on the title clearing the floor; that is a real
  remaining limitation, not a solved problem.
- **No free bonus.** With a single surviving candidate there is nothing
  to compare, so the semantic weight is redistributed across title and
  keyword instead of granted. Handing out a constant is a disguised
  threshold change - and while calibrating, it was enough to let "Senior
  Accountant" clear the match floor.
- **The Stage 2 gate uses the combined match confidence instead.** On the
  same 650 postings that admits 221 (34%) and gives everything else
  exactly 0 - an actual cost control rather than one in name only.

Character n-grams still earn their place: they give the matcher
morphological reach ("train"/"trainer"/"training"/"trainings" share
n-grams), so a posting does not have to inflect words the way the CV
does.

### 8.4 Gig work, without scraping a login-only platform

Outlier AI still has no public API and is still not scraped. But the
premise that this blocked the gig channel was wrong: **the AI-data
marketplaces publish independent-contractor project work on the very same
public ATS boards as their staff roles**. Appen's Lever board carries
"[Croatian] - Voice Recording Specialist: Join our team as an Independent
Contractor for Project Morava"; Cohere's Ashby board carries part-time
independent-contractor annotation work.

So the working gig channel is `gigs/classifier.py` - a classifier over
postings this app already collects legitimately - plus
`config/manual_gigs.yaml` for anything found on a platform that publishes
nothing. Gigs now get a `gigs` row, a `gig_analysis` row with the full
score breakdown (the table §4 promised but never created), the
`GIG_PROJECT_WORK` opportunity class, and a dashboard feed that shows
rate, hours, duration and component scores.

### 8.5 Notifications and CV tailoring

Notifications: a real SMTP adapter joins hardened Telegram/Slack
adapters, all opt-in, all failing soft (a dead channel is a reported
failure, never an exception that aborts a run). Urgent alerts fire **once
per job**, tracked in the new `notification_log` table - a notifier that
re-alerts every morning trains its reader to ignore it. Thresholds moved
from a hard-coded constant into `config/profile.yaml`.

CV tailoring (`tailoring/`) produces a per-posting brief - which evidence
to lead with, which requirements the CV does not support, which of the
posting's terms are safe to mirror - and a cover-letter draft assembled
only from `cv_evidence_map.json` entries, recording the evidence ids it
used. An LLM may rewrite the draft for tone; the rewrite is validated
against the same anti-fabrication rules and **discarded if it invents
anything** (a completed MSc, a language the CV does not evidence, US work
authorization, a clearance). The failure mode is plainer prose, never a
false claim in a document Richard sends under his own name.

### 8.6 What is still genuinely not collected

Two things, both surfaced in the dashboard's Source Health tab rather
than implied to be covered:

1. **Meta careers** - serves listings through an authenticated GraphQL
   endpoint with no public JSON search API, and has no public
   Greenhouse/Lever/Ashby board. This is the one Tier-1 strategic
   employer with no collectable channel at all.
2. **Outlier AI and comparable login-only gig marketplaces** - unchanged
   from §1. Manual entry is the supported route.

Hugging Face was probed under four plausible tokens and has no public
board either; it stays `UNVERIFIED` rather than being quietly dropped
from the watchlist.

## 9. Bugs found against real collected data (2026-08-22)

The same lesson as §7, and it landed the same way: a live run over 650
real postings from four boards surfaced three defects that 138 passing
tests had not.

1. **Permanent roles classified as gig work.** An Anthropic "Hardware Lab
   Manager" posting mentions overseeing "contractor work on-site
   (electricians, cabling crews)"; an accounts-receivable role mentions
   "as-needed" support. The first version of `gigs/classifier.py` treated
   any mention of contract work as a strong signal and misclassified
   both, along with 10 other Anthropic roles. Fixed by splitting signals
   into *self-referential* (the posting calls **itself** contract or
   project work) and *supporting* (ambiguous alone), and requiring either
   a self-referential signal, or an hourly rate plus corroboration. Gig
   count on the same data went from 42 (10 wrong) to 32 (all correct).
2. **`employment_type` mis-detected as CONTRACT.** The same "contractor
   work on-site" phrase made `normalize/normalizer.py` type a permanent
   role as CONTRACT, because its pattern was a bare `\bcontract(or)?\b`.
   That fed the gig classifier and would also have shown the wrong
   employment type on the dashboard card. Now requires self-referential
   phrasing.
3. **"team" as a keyword false-anchor.** `_keywords_from_titles` extracted
   "team" from ai_security's "AI Red Team" example titles, where it then
   matched the phrase "enterprise teams" in the boilerplate of a pure
   training posting - enough to hand a Generative AI Trainer role to the
   AI-security family. Same class as the "enablement" bug in §7.3, one
   level down in the keyword channel rather than the title channel. Fixed
   by extending the generic-noun stopword list; regression test in
   `tests/test_embeddings.py`.

A fourth improvement came out of the same run rather than being a bug:
the AI-data marketplaces publish large numbers of language-specific
contractor projects ("[Croatian] - Voice Recording Specialist"), and the
CV evidences English only. These are now a **mandatory** mismatch rather
than a soft gap, and `find_mismatches()` reads the job title as well as
the description, because the language marker is frequently in the title
alone.

## 10. Independent review pass (2026-08-22)

The completed work was put through an adversarial review before being
finalised. Six defects were confirmed, all of which the 157 passing tests
missed, and all are fixed. Recording them here because five of the six
are the same species of bug: **a control that looks like it works,
measured against nothing.**

1. **The Stage 2 cost gate was a no-op** (and, on long postings, an
   accidental blanket block). Fixed by re-founding it on the combined
   match confidence and calibrating both against 650 real postings - see
   §8.3.
2. **The semantic rescue path was unreachable**, and its test passed for
   the wrong reason: the posting it used had a fuzzy title ratio of 1.0,
   so the rescue branch never ran. The path is deleted and the test now
   asserts the real, measured limitation instead of a capability the code
   never had.
3. **The anti-fabrication guardrails missed the most natural phrasings.**
   The claim-verb list had `completed|holds|earned|my` but not `have`, so
   *"I have an MSc in Data Analytics"* - the single most likely way for a
   model to state the exact claim the guardrail exists to prevent -
   validated clean. The same gap covered `"I have a PhD"`. Separately,
   the guardrail's language list had drifted to 14 entries against the
   negative matcher's ~50, so a letter could claim fluent Dutch, Polish,
   Croatian, Swedish or Ukrainian. Both lists are now one list, and the
   verb list is shared across rules.
4. **The language-requirement rule fired on postings requiring only
   English.** "Fluent English required; German is a plus", "you will
   support our Spanish speaking customers", even "proficient with French
   press coffee machines" each produced a *mandatory* mismatch - which
   hard-caps the score at 55 and deletes an eligible role from the feed.
   Worse, the tailoring generator then quoted the invented requirement
   back at the employer. Now clause-scoped and requirement-scoped: a
   language counts only when its own clause also carries a requirement
   marker, and "a plus"/"nice to have" downgrades it to a preferred gap.
5. **`search_discovery.max_queries_per_run` was read by nothing** - the
   knob bounding outbound request volume silently had no effect.
6. **One `job_sources` SELECT per known posting per run**, purely to pick
   a minimum over a handful of rows. Now reads the already-loaded
   relationship.

Two further fixes came out of chasing (1)-(2): a single-word example
title stripped of stopwords ("Training Content Developer" -> "content")
was matching unrelated titles at the character level, which let "Senior
Accountant" match `technical_instructional_design` at 0.71; a shared-word
requirement now gates that. And the cover letter no longer presents this
app's paraphrase of a requirement as a quotation from the employer's
advert - it says "As I read the role, it calls for X", because putting
words in an employer's mouth in a letter addressed to them is its own
kind of fabrication.
