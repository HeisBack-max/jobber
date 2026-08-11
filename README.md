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

- `config/sources.yaml` - the ATS boards actually polled by
  `jobintel collect` (Greenhouse/Lever/Ashby board tokens).
- `config/strategic_companies.yaml` - the full strategic watchlist,
  including companies without a working collector yet (see
  `verification_status` / `notes` on each entry).
- `config/search_queries.yaml` - query families for a future
  search-discovery collector.

Before relying on a new board token, verify it's live:

```bash
jobintel verify-boards
```

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
that hasn't been scored yet for the current profile version, then (if
`ANTHROPIC_API_KEY` is set and the deterministic pre-score clears the
Stage 4 threshold in `config/scoring.yaml`) sends it for a bounded LLM
refinement pass.

## Full daily run

```bash
jobintel run
```

Equivalent to `collect` + `evaluate` + printing the daily digest.

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
