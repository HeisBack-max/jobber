"""jobintel CLI - the only interface Richard needs for day-to-day use.

    jobintel run           # full pipeline: collect -> analyze -> notify -> digest
    jobintel collect       # collection only
    jobintel evaluate      # scoring/LLM evaluation + gig identification
    jobintel digest        # print today's digest
    jobintel dashboard     # launch the Streamlit dashboard
    jobintel verify-boards # check configured ATS board tokens are alive
    jobintel verify-search # check the search-discovery backends are reachable
    jobintel tailor        # CV-tailoring brief + cover-letter draft for a job
    jobintel notify        # send pending alerts / test the configured channels
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import click
import structlog

logger = structlog.get_logger()


@click.group()
def main() -> None:
    """Remote Job Intelligence - Richard Best's personal opportunity analyst."""


@main.command()
def collect() -> None:
    """Run all configured collectors and store new/updated jobs."""
    from jobintel.pipeline import run_collection

    summary = asyncio.run(run_collection())
    click.echo(summary.render())


@main.command()
def evaluate() -> None:
    """Run geography classification, matching, scoring and gig identification."""
    from jobintel.pipeline import run_evaluation

    summary = run_evaluation()
    click.echo(summary.render())


@main.command()
@click.option("--no-notify", is_flag=True, help="Skip notification dispatch for this run.")
def run(no_notify: bool) -> None:
    """Full pipeline: collect, evaluate, notify, then print the digest."""
    from jobintel.digest.generator import generate_digest
    from jobintel.pipeline import run_collection, run_evaluation

    collect_summary = asyncio.run(run_collection())
    click.echo(collect_summary.render())
    eval_summary = run_evaluation()
    click.echo(eval_summary.render())

    if not no_notify:
        from jobintel.notifications.dispatch import dispatch_notifications

        click.echo(asyncio.run(dispatch_notifications()).render())

    click.echo(generate_digest().render_text())


@main.command()
def digest() -> None:
    """Print today's digest of new worthwhile opportunities."""
    from jobintel.digest.generator import generate_digest

    click.echo(generate_digest().render_text())


@main.command()
def dashboard() -> None:
    """Launch the Streamlit dashboard."""
    app_path = Path(__file__).resolve().parents[2] / "dashboard" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)


@main.command("verify-boards")
@click.option("--muted", is_flag=True, help="Check only the muted (not-yet-verified) boards.")
def verify_boards(muted: bool) -> None:
    """Live-check every configured ATS board token and report health."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from verify_boards import verify_all  # type: ignore[import-not-found]

    asyncio.run(verify_all(muted_only=muted))


@main.command("verify-search")
def verify_search() -> None:
    """Check whether the search-discovery backends are reachable.

    They ship disabled: this is what tells you a backend actually works
    before config/search_queries.yaml starts depending on it.
    """
    from jobintel.collectors.base import SourceError
    from jobintel.discovery.search import SEARCH_BACKENDS

    async def check_all() -> None:
        for name, factory in SEARCH_BACKENDS.items():
            source = factory(families=None, max_queries=1)
            try:
                jobs = await source.discover()
                click.echo(f"{name:<12} OK    - {len(jobs)} jobs returned for one query")
            except SourceError as exc:
                click.echo(f"{name:<12} FAIL  - {exc}")
            except Exception as exc:  # noqa: BLE001
                click.echo(f"{name:<12} FAIL  - unexpected error: {exc}")
        click.echo(
            "\nEnable a working backend under `search_discovery.backends` in "
            "config/search_queries.yaml."
        )

    asyncio.run(check_all())


@main.command()
@click.argument("job_id")
@click.option("--no-llm", is_flag=True, help="Skip the optional LLM rewrite pass.")
@click.option("--save/--no-save", default=True, help="Store the generated material against the job.")
def tailor(job_id: str, no_llm: bool, save: bool) -> None:
    """Generate a CV-tailoring brief and cover-letter draft for JOB_ID.

    Every claim comes from config/cv_evidence_map.json; anything an LLM
    rewrite invents is rejected before it reaches you.
    """
    from jobintel.tailoring.service import generate_and_store_materials, generate_materials

    if save:
        result = asyncio.run(generate_and_store_materials(job_id, use_llm=not no_llm))
    else:
        from jobintel.db.models import Job
        from jobintel.db.session import session_scope

        with session_scope() as session:
            job = session.query(Job).filter_by(id=job_id).first()
            if job is None:
                raise click.ClickException(f"no job with id {job_id}")
            title, company, description = job.job_title, job.company_name, job.job_description_clean
        result = asyncio.run(generate_materials(title, company, description, use_llm=not no_llm))

    click.echo(result.render_text())


@main.command()
@click.option("--test", "test_only", is_flag=True, help="Send a test message to every configured channel.")
def notify(test_only: bool) -> None:
    """Dispatch pending urgent alerts and the daily digest."""
    from jobintel.notifications.dispatch import dispatch_notifications, send_test_message

    summary = asyncio.run(send_test_message() if test_only else dispatch_notifications())
    click.echo(summary.render())
    if not summary.channels:
        click.echo(
            "Configure at least one of JOBINTEL_TELEGRAM_*, JOBINTEL_SLACK_WEBHOOK_URL, "
            "or JOBINTEL_SMTP_HOST + JOBINTEL_NOTIFICATION_EMAIL_TO in .env to enable alerts."
        )


if __name__ == "__main__":
    main()
