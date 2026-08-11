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
  Lever/Ashby boards.** The spec assumes these are checked "deliberately"
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
  login.** No public, unauthenticated job-listing API exists. Building a
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

Explicitly deferred (documented, not silently dropped - see spec §61
"Future Phases" for precedent):

- Live collectors for companies without a public Greenhouse/Lever/Ashby
  board (OpenAI, Google, Microsoft, Amazon, Meta, etc.) - registry +
  source-health placeholders exist; a career-site/search-discovery
  collector is future work.
- A working Outlier AI (or similar) gig collector (requires authenticated
  access - out of scope until Richard provides a ToS-compliant path).
- Embedding-based semantic retrieval (keyword/role-family matching is
  used for the MVP semantic pre-score, per spec §32 "Use keyword and/or
  embedding/semantic methods").
- Notification adapters beyond the interface (email/Telegram/Slack are
  wired as optional, disabled-by-default stubs behind one interface -
  spec explicitly says these "must not be required for MVP operation").
- CV tailoring / cover-letter generation (spec §39: design for it later,
  don't prioritize now).

## 3. Configuration model

See `config/profile.yaml` (candidate + preferences + geography rules),
`config/roles.yaml` (role taxonomy + negative-matching signals),
`config/sources.yaml` (ATS board registry actually polled),
`config/strategic_companies.yaml` (full strategic watchlist incl.
companies without a working collector yet), `config/search_queries.yaml`
(future search-discovery queries), `config/scoring.yaml` (every scoring
weight/threshold), `config/cv_evidence_map.json` (CV-grounded evidence,
factual authority per the spec's precedence rule).

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
  hours) + `gig_analysis` for gig_quality_score breakdown
- `application_status` — status history with timestamps + notes +
  recruiter contact fields
- `feedback` — 👍/👌/👎/🚫 + reason, used for transparent ranking
  adjustment (not opaque retraining, per spec §38)
- `source_health` — per-run collection stats per source
- `llm_usage` — tokens/cost/provider/model per evaluation call, for
  `cost_control.daily_llm_budget_usd` enforcement

## 5. Development order followed

Milestones 1→5 implemented fully and tested. Milestone 6 implemented as
registry + framework (see §1/§2 above for what's live vs. deferred).
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
