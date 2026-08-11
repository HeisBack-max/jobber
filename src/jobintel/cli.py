"""jobintel CLI - the only interface Richard needs for day-to-day use.

    jobintel run          # full pipeline: collect -> analyze -> digest
    jobintel collect       # collection only
    jobintel evaluate      # run scoring/LLM evaluation on uncored jobs
    jobintel digest        # print today's digest
    jobintel dashboard     # launch the Streamlit dashboard
    jobintel verify-boards # check configured ATS board tokens are alive
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
    """Run geography classification, matching, and scoring on pending jobs."""
    from jobintel.pipeline import run_evaluation

    summary = run_evaluation()
    click.echo(summary.render())


@main.command()
def run() -> None:
    """Full pipeline: collect, then evaluate, then print the digest."""
    from jobintel.digest.generator import generate_digest
    from jobintel.pipeline import run_collection, run_evaluation

    collect_summary = asyncio.run(run_collection())
    click.echo(collect_summary.render())
    eval_summary = run_evaluation()
    click.echo(eval_summary.render())
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
def verify_boards() -> None:
    """Live-check every configured ATS board token and report health."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from verify_boards import verify_all  # type: ignore[import-not-found]

    asyncio.run(verify_all())


if __name__ == "__main__":
    main()
