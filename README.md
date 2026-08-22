# Remote Job Intelligence

A personal opportunity-discovery, eligibility, ranking, and intelligence
system for Richard Best. See `IMPLEMENTATION_PLAN.md` for scope decisions
and `ARCHITECTURE.md` for the system design and data-flow diagram.

This is not a job scraper - it discovers, deduplicates, geographically
filters, scores, and explains a small number of genuinely worthwhile
remote-compatible opportunities per day (signal over volume).

## Prerequisites

- Python 3.12+
- (Optional) an Anthropic API key, for the Stage 3 LLM evaluation refinement.
  The app is fully functional without one - jobs are scored deterministically
  and simply don't get the LLM refinement pass.

## Installation

```bash
git clone <this repo>
cd jobber
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Environment configuration

```bash
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY if you want Stage 3 LLM evaluation.
# Everything else has a sensible default for local SQLite operation.
```

## Database setup (migrations)

```bash
alembic upgrade head
```

This creates `data/jobintel.db` (SQLite) and applies the full schema.
Re-run `alembic upgrade head` after pulling changes that add new
migrations under `alembic/versions/`.

## CV / profile configuration

- `config/profile.yaml` - Richard's geography rules, remote priority, and
  scoring thresholds. Edit this to change preferences; no code changes
  needed.
- `config/cv_evidence_map.json` - structured evidence extracted directly
  from Richard's master CV. **Do not add claims here that aren't
  supported by the actual CV** - this file is the factual authority the
  matching/explanation engine cites.
- `config/roles.yaml` - the role taxonomy (Tier A/B/C + emerging
  categories) and negative-matching signal categories.

## Source configuration

- `config/sources.yaml` - the boards actually polled by `jobintel
  collect`: 75 verified employer boards across Greenhouse, Lever and
  Ashby, plus muted (shipped-but-unverified) entries for Workday and the
  Microsoft/Amazon/Google career-site collectors. Supported `ats` values:
  `greenhouse`, `lever`, `ashby`, `workday`, `smartrecruiters`,
  `workable`, `recruitee`, `careersite_microsoft`, `careersite_amazon`,
  `careersite_google`.
- `config/strategic_companies.yaml` - the full strategic watchlist,
  including companies without a working collector yet (see
  `verification_status` / `notes` on each entry).
- `config/search_queries.yaml` - query families for the search-discovery
  collectors and the career-site collectors' keyword terms. Both
  aggregator backends (Remotive, RemoteOK) ship **disabled**; enable them
  under `search_discovery.backends` once `jobintel verify-search`
  confirms they are reachable from your network.
- `config/manual_gigs.yaml` - gigs you enter by hand, for platforms that
  publish no API (Outlier AI and similar). Anything pasted here is
  scored, ranked and digested like a collected opportunity.

Before relying on a new board token, verify it is live **and belongs to
the company you think it does**:

```bash
jobintel verify-boards          # check every configured board
jobintel verify-boards --muted  # check only the not-yet-verified ones
jobintel verify-search          # check the search-discovery backends
```

A board answering 200 is not proof of identity: `greenhouse:cohere` is a
healthcare company, `greenhouse:figure` is not Figure AI, and
`ashby:runway` is a business-planning startup, not RunwayML. Read a
sample posting before promoting a token to `VERIFIED`.

Entries with `collection_status: muted` ship with a working adapter but
are never polled until you verify the token and change their status -
that is how a source is added without inventing coverage that does not
exist.

## Collecting opportunities

```bash
jobintel collect
```

Runs every configured collector, normalizes results into the canonical
schema, deduplicates against existing opportunities, and persists new/
updated jobs. One broken source never aborts the whole run - check the
printed summary and the dashboard's Source Health tab for details.

## Evaluating opportunities

```bash
jobintel evaluate
```

Runs the deterministic geography/matching/scoring pipeline on any job
that hasn't been scored yet for the current profile version, identifies
and separately scores gig/project work, and then - if `ANTHROPIC_API_KEY`
is set and the job clears *both* cost-control gates in
`config/scoring.yaml` (`stage2_semantic_prescore_min_to_advance` and
`stage4_deep_analysis_min_score`) - sends it for a bounded LLM refinement
pass.

Matching combines three channels, all weighted in
`config/scoring.yaml` under `semantic_matching`: fuzzy title similarity,
keyword overlap, and vector-space document similarity (TF-IDF cosine over
word and character n-grams, fitted on the role taxonomy plus your CV
evidence). The third channel is what lets a posting match on meaning when
it does not reuse the CV's vocabulary - and what stops boilerplate
keyword noise from inflating a borderline title match.

## Gigs and project work

Gigs are found two ways, both ToS-compliant:

1. **Automatically** - contractor and project postings published on the
   ordinary public boards of the AI-data marketplaces this app already
   collects (Appen, Mercor, Toloka, Turing, Prolific, Invisible,
   Labelbox, Snorkel). `jobintel evaluate` classifies them, extracts
   hourly rate / weekly hours / duration, and scores them on the gig
   model rather than the career model.
2. **By hand** - paste anything from a platform that publishes no API
   into `config/manual_gigs.yaml`.

Outlier AI is deliberately not scraped: its listings require a logged-in
account and it publishes no API. See `src/jobintel/gigs/outlier.py`.

## Tailoring a CV / cover letter

```bash
jobintel tailor <job_id>            # brief + cover-letter draft
jobintel tailor <job_id> --no-llm   # deterministic only, no API call
```

Produces a tailoring brief (which CV evidence to lead with for *this*
posting, which of its requirements your CV does not support, which of its
terms you can safely mirror) and a cover-letter draft assembled only from
entries in `config/cv_evidence_map.json`. With an API key configured, an
LLM may rewrite the draft for tone - and the rewrite is thrown away if it
introduces any claim the CV does not support (a completed MSc, another
language, US work authorization, a clearance). The dashboard exposes the
same thing behind the "Tailor CV" button, deterministic-only so a click
never spends money.

## Notifications

Every channel is opt-in and none is required:

```bash
jobintel notify --test   # prove your channels work
jobintel notify          # send pending urgent alerts + today's digest
```

Configure any of Telegram, Slack or SMTP email in `.env` (see
`.env.example`). Urgent-alert thresholds live in `config/profile.yaml`
under `alerts:`; an urgent alert fires **once per job**, tracked in the
`notification_log` table, so a re-run never re-alerts. `jobintel run` and
`scripts/daily_run.py` dispatch notifications automatically.

## Full daily run

```bash
jobintel run
```

Equivalent to `collect` + `evaluate` + notify + printing the daily
digest. Use `jobintel run --no-notify` to skip the notification step.

## Starting the dashboard

```bash
jobintel dashboard
```

Opens the Streamlit dashboard at `http://localhost:8501` with the
required feeds (Best Matches Today, True Remote, Frontier AI/Strategic,
Vertex AI & Gemini, Gigs & Quicker Income, Interesting Wildcards, Newly
Discovered, Source Health), filters, and per-opportunity actions
(Open Job / Interested / Applied / Not Interested / Explain Match /
feedback reactions).

## Scheduling daily runs

Simplest option - a system cron entry:

```cron
0 6 * * * /path/to/jobber/.venv/bin/python /path/to/jobber/scripts/daily_run.py >> /path/to/jobber/data/daily_run.log 2>&1
```

Alternative - a persistent process using APScheduler:

```bash
python -m jobintel.scheduler.daily
```

## Backups

The entire application state is `data/jobintel.db` (SQLite, git-ignored).
Back it up with a plain file copy:

```bash
cp data/jobintel.db data/backups/jobintel-$(date +%Y%m%d).db
```

## Migrations / upgrades

```bash
git pull
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

To create a new migration after changing `src/jobintel/db/models.py`:

```bash
alembic revision --autogenerate -m "describe the change"
```

Always review the generated migration before applying it.

## Troubleshooting

- **A source returns zero jobs and you suspect a bad token**: run
  `jobintel verify-boards` - a 404 means the board token needs updating
  in `config/sources.yaml`, not that the company has no open roles.
- **Dashboard shows no opportunities**: run `jobintel collect` then
  `jobintel evaluate` first - the dashboard only reads from the database,
  it never collects live.
- **LLM refinement never runs**: confirm `ANTHROPIC_API_KEY` is set in
  `.env` and that jobs are clearing the `stage4_deep_analysis_min_score`
  threshold in `config/scoring.yaml` - low-scoring jobs intentionally skip
  the paid LLM stage.
- **A muted board never collects anything**: that is intentional - muted
  means "adapter ships, token unproven". Run `jobintel verify-boards
  --muted`, then set `collection_status` to `normal` (or higher) for the
  ones that come back OK.
- **A source suddenly reports BROKEN with "unexpected payload shape"**:
  the upstream API changed. That is deliberately loud rather than
  silently returning zero jobs, which would hide a whole employer from
  your feed.
- **A generated cover letter looks plainer than expected**: an LLM
  rewrite was probably rejected by the anti-fabrication guardrails. The
  output says so explicitly, listing which claim tripped which rule.
- **"database is locked" errors**: SQLite only supports one writer at a
  time - don't run `jobintel collect`/`evaluate` and the dashboard's
  write actions (Applied/feedback buttons) at the exact same moment on a
  heavily concurrent setup; for a single personal user this essentially
  never happens in practice.

## Running tests

```bash
pytest
ruff check src/ tests/ scripts/ dashboard/
```

## Project structure

See `ARCHITECTURE.md` §4 for the full package layout and rationale.
