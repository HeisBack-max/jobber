"""Optional APScheduler wiring for a persistent daily_run process (spec
§8/§56). Not required for MVP operation - `jobintel run` invoked via cron
or a system scheduler works just as well; this is for anyone who wants a
single long-running process instead."""

from __future__ import annotations

import asyncio

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler

logger = structlog.get_logger()


def _run_daily_job() -> None:
    from jobintel.digest.generator import generate_digest
    from jobintel.pipeline import run_collection, run_evaluation

    collect_summary = asyncio.run(run_collection())
    logger.info("scheduler.collection_complete", summary=collect_summary.render())
    eval_summary = run_evaluation()
    logger.info("scheduler.evaluation_complete", summary=eval_summary.render())
    digest = generate_digest()
    logger.info("scheduler.digest_generated", text=digest.render_text())
    from jobintel.notifications.dispatch import dispatch_notifications

    notify_summary = asyncio.run(dispatch_notifications())
    logger.info("scheduler.notifications_dispatched", summary=notify_summary.render())


def start_daily_scheduler(hour: int = 6, minute: int = 0) -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(_run_daily_job, "cron", hour=hour, minute=minute, id="daily_run")
    logger.info("scheduler.starting", hour=hour, minute=minute)
    scheduler.start()


if __name__ == "__main__":
    start_daily_scheduler()
