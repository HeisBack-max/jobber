"""Notification adapter + dispatch tests (spec §43/§44).

No network and no SMTP server: adapters are exercised through mocked
transports, because the behaviour worth testing is the policy (who gets
alerted, once) and the failure handling (a broken channel must not break
the run), not httpx itself.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from jobintel.notifications.base import (
    EmailAdapter,
    NotificationAdapter,
    SlackAdapter,
    TelegramAdapter,
    get_enabled_adapters,
    urgent_alert_condition,
)
from jobintel.notifications.dispatch import (
    URGENT_ALERT,
    dispatch_notifications,
    find_urgent_opportunities,
    send_test_message,
)


class RecordingAdapter(NotificationAdapter):
    name = "recording"

    def __init__(self, fail_times: int = 0):
        self.messages: list[tuple[str, str]] = []
        self._fail_times = fail_times
        self.attempts = 0

    async def _deliver(self, subject: str, body: str) -> None:
        self.attempts += 1
        if self.attempts <= self._fail_times:
            raise RuntimeError("simulated transport failure")
        self.messages.append((subject, body))


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    """Retry backoff is real seconds in production; tests must not pay it."""
    monkeypatch.setattr("jobintel.notifications.base.RETRY_BACKOFF_SECONDS", 0)


def test_no_channels_configured_means_nothing_is_sent(monkeypatch):
    """A fresh checkout must notify nobody - notifications are opt-in and
    must never be required for the app to run (spec §44)."""
    from jobintel import settings as settings_module

    settings_module.get_settings.cache_clear()
    for var in ("JOBINTEL_TELEGRAM_BOT_TOKEN", "JOBINTEL_TELEGRAM_CHAT_ID",
                "JOBINTEL_SLACK_WEBHOOK_URL", "JOBINTEL_SMTP_HOST", "JOBINTEL_NOTIFICATION_EMAIL_TO"):
        monkeypatch.delenv(var, raising=False)
    assert get_enabled_adapters() == []
    settings_module.get_settings.cache_clear()


def test_each_channel_activates_only_with_its_own_settings(monkeypatch):
    from jobintel import settings as settings_module

    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("JOBINTEL_SLACK_WEBHOOK_URL", "https://hooks.slack.test/abc")
    monkeypatch.setenv("JOBINTEL_SMTP_HOST", "smtp.test")
    monkeypatch.setenv("JOBINTEL_NOTIFICATION_EMAIL_TO", "richard@example.com")
    # A bot token with no chat id is incomplete and must NOT activate.
    monkeypatch.setenv("JOBINTEL_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.delenv("JOBINTEL_TELEGRAM_CHAT_ID", raising=False)

    names = {a.name for a in get_enabled_adapters()}
    assert names == {"slack", "email"}
    settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_adapter_retries_then_succeeds():
    adapter = RecordingAdapter(fail_times=2)
    result = await adapter.send("subject", "body")
    assert result.ok
    assert adapter.attempts == 3
    assert adapter.messages == [("subject", "body")]


@pytest.mark.asyncio
async def test_adapter_failure_is_reported_not_raised():
    """A dead channel must degrade to a reported failure - never an
    exception that aborts a collection or evaluation run."""
    adapter = RecordingAdapter(fail_times=99)
    result = await adapter.send("subject", "body")
    assert result.ok is False
    assert "simulated transport failure" in result.error


@pytest.mark.asyncio
async def test_telegram_non_200_is_a_failure(httpx_mock):
    httpx_mock.add_response(
        url="https://api.telegram.org/botTOKEN/sendMessage",
        status_code=401,
        json={"ok": False, "description": "Unauthorized"},
        is_reusable=True,
    )
    result = await TelegramAdapter("TOKEN", "chat-1").send("subject", "body")
    assert result.ok is False
    assert "401" in result.error


@pytest.mark.asyncio
async def test_telegram_splits_messages_over_the_api_limit(httpx_mock):
    httpx_mock.add_response(url="https://api.telegram.org/botTOKEN/sendMessage", json={"ok": True}, is_reusable=True)
    long_body = "x" * 9000
    result = await TelegramAdapter("TOKEN", "chat-1").send("subject", long_body)
    assert result.ok
    # 9000+ chars cannot go in one Telegram message; it must be chunked
    # rather than rejected wholesale by the API.
    assert len(httpx_mock.get_requests()) >= 3


@pytest.mark.asyncio
async def test_slack_posts_webhook(httpx_mock):
    httpx_mock.add_response(url="https://hooks.slack.test/abc", text="ok")
    result = await SlackAdapter("https://hooks.slack.test/abc").send("Daily brief", "2 matches")
    assert result.ok
    assert b"Daily brief" in httpx_mock.get_requests()[0].content


@pytest.mark.asyncio
async def test_email_adapter_builds_and_sends_a_message(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"], sent["port"] = host, port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, user, password):
            sent["login"] = user

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    adapter = EmailAdapter("smtp.test", 587, "user", "pass", "from@example.com", ["to@example.com"])
    result = await adapter.send("Daily brief", "2 matches")

    assert result.ok
    assert sent["starttls"] is True
    assert sent["login"] == "user"
    assert sent["message"]["To"] == "to@example.com"
    assert "2 matches" in sent["message"].get_content()


def test_urgent_alert_thresholds_come_from_config():
    assert urgent_alert_condition(95, 3, True, True) is True
    assert urgent_alert_condition(91, 3, True, True) is False       # below score bar
    assert urgent_alert_condition(95, 48, True, True) is False      # too old
    assert urgent_alert_condition(95, 3, False, True) is False      # not eligible
    assert urgent_alert_condition(95, 3, True, False) is False      # remote not confirmed


def _seed_urgent_job(temp_db, score=95.0):
    from jobintel.db.models import Job, JobAnalysisRecord

    with temp_db.session_scope() as session:
        job = Job(
            source="greenhouse", source_job_id="1", source_url="https://example.com/1",
            canonical_url="https://example.com/1", company_name="Acme AI",
            job_title="Generative AI Trainer", normalized_job_title="generative ai trainer",
            remote_classification="REMOTE_WORLDWIDE", candidate_geographically_eligible="YES",
            published_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2),
            content_hash="hash-1",
        )
        session.add(job)
        session.flush()
        job_id = job.id
        session.add(JobAnalysisRecord(
            job_id=job_id, profile_version="v1", remote_score=25, experience_score=25,
            skills_score=10, training_advantage_score=10, ai_cyber_intersection_score=5,
            interview_probability_score=15, compensation_score=5, freshness_score=5,
            can_do_score=90, desirability_score=90, overall_score=score, confidence_score=90,
            recommendation="EXCEPTIONAL_MATCH", reasoning_summary="Strong match.",
            strengths=["Direct AI training experience."],
        ))
    return job_id


def test_urgent_alert_fires_once_per_job(temp_db):
    """The dedupe rule that makes alerts worth reading: run the pipeline
    twice and the same job must not be alerted twice."""
    job_id = _seed_urgent_job(temp_db)
    adapter = RecordingAdapter()

    summary = asyncio.run(dispatch_notifications(adapters=[adapter], include_digest=False))
    assert summary.urgent_alerts_sent == 1
    assert job_id in adapter.messages[0][1] or "Generative AI Trainer" in adapter.messages[0][0]

    summary2 = asyncio.run(dispatch_notifications(adapters=[adapter], include_digest=False))
    assert summary2.urgent_alerts_sent == 0
    assert len(adapter.messages) == 1

    from jobintel.db.models import NotificationLog
    with temp_db.session_scope() as session:
        logs = session.query(NotificationLog).filter_by(kind=URGENT_ALERT).all()
        assert len(logs) == 1
        assert logs[0].status == "SENT"


def test_low_scoring_job_never_triggers_an_urgent_alert(temp_db):
    _seed_urgent_job(temp_db, score=80.0)
    with temp_db.session_scope() as session:
        assert find_urgent_opportunities(session) == []


def test_failed_delivery_is_logged_and_does_not_suppress_a_retry(temp_db):
    """A failed send must not count as "already alerted" - otherwise a
    transient outage silently swallows the alert forever."""
    _seed_urgent_job(temp_db)
    failing = RecordingAdapter(fail_times=99)

    summary = asyncio.run(dispatch_notifications(adapters=[failing], include_digest=False))
    assert summary.urgent_alerts_sent == 0
    assert summary.failures

    working = RecordingAdapter()
    summary2 = asyncio.run(dispatch_notifications(adapters=[working], include_digest=False))
    assert summary2.urgent_alerts_sent == 1


def test_test_message_reaches_every_configured_channel():
    adapters = [RecordingAdapter(), RecordingAdapter()]
    summary = asyncio.run(send_test_message(adapters=adapters))
    assert summary.digests_sent == 2
    assert all(a.messages for a in adapters)
