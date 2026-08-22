"""Alert adapters (spec §44).

None of these are required for the app to work: every adapter is
disabled unless its own configuration is present, and
`get_enabled_adapters()` returns an empty list when nothing is
configured. What they are *not* allowed to do is fail loudly - a
temporarily unreachable Telegram must never abort a collection run or
lose a digest, so every adapter catches its own transport errors and
reports a NotificationResult instead of raising.
"""

from __future__ import annotations

import asyncio
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage

import structlog

from jobintel.settings import get_settings, load_profile

logger = structlog.get_logger()

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


@dataclass
class NotificationResult:
    channel: str
    ok: bool
    error: str | None = None


class NotificationAdapter(ABC):
    name: str

    @abstractmethod
    async def _deliver(self, subject: str, body: str) -> None:
        """Perform the actual delivery, raising on failure."""

    async def send(self, subject: str, body: str) -> NotificationResult:
        """Deliver with bounded retries, never raising at the caller."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                await self._deliver(subject, body)
                return NotificationResult(self.name, True)
            except Exception as exc:  # noqa: BLE001 - a broken channel must not break the run
                last_error = exc
                logger.warning("notifications.delivery_failed", channel=self.name, attempt=attempt, error=str(exc))
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)
        logger.error("notifications.giving_up", channel=self.name, error=str(last_error))
        return NotificationResult(self.name, False, str(last_error))


class TelegramAdapter(NotificationAdapter):
    name = "telegram"
    MAX_MESSAGE_CHARS = 4096  # Telegram's hard limit; longer messages are rejected outright.

    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def _deliver(self, subject: str, body: str) -> None:
        import httpx

        text = f"{subject}\n\n{body}"
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in _chunk(text, self.MAX_MESSAGE_CHARS):
                response = await client.post(url, json={"chat_id": self._chat_id, "text": chunk})
                if response.status_code != 200:
                    # Telegram answers 200 for accepted sends; anything else
                    # (401 bad token, 400 bad chat_id) is a real failure that
                    # must be reported rather than silently swallowed.
                    raise RuntimeError(f"telegram returned {response.status_code}: {response.text[:200]}")


class SlackAdapter(NotificationAdapter):
    name = "slack"

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def _deliver(self, subject: str, body: str) -> None:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self._webhook_url, json={"text": f"*{subject}*\n{body}"})
            if response.status_code != 200:
                raise RuntimeError(f"slack webhook returned {response.status_code}: {response.text[:200]}")


class EmailAdapter(NotificationAdapter):
    """Plain SMTP. Runs the blocking smtplib call in a worker thread so it
    doesn't stall the event loop the collectors share."""

    name = "email"

    def __init__(self, host: str, port: int, username: str | None, password: str | None,
                 sender: str, recipients: list[str], use_tls: bool = True):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._recipients = recipients
        self._use_tls = use_tls

    def _send_sync(self, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message.set_content(body)

        if self._port == 465:
            server = smtplib.SMTP_SSL(self._host, self._port, timeout=30)
        else:
            server = smtplib.SMTP(self._host, self._port, timeout=30)
        with server:
            if self._port != 465 and self._use_tls:
                server.starttls()
            if self._username and self._password:
                server.login(self._username, self._password)
            server.send_message(message)

    async def _deliver(self, subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, subject, body)


def _chunk(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[i:i + size] for i in range(0, len(text), size)]


def get_enabled_adapters() -> list[NotificationAdapter]:
    """Every channel is opt-in: an adapter exists only when its own
    settings are present, so a fresh checkout notifies nobody."""
    settings = get_settings()
    adapters: list[NotificationAdapter] = []
    if settings.telegram_bot_token and settings.telegram_chat_id:
        adapters.append(TelegramAdapter(settings.telegram_bot_token, settings.telegram_chat_id))
    if settings.slack_webhook_url:
        adapters.append(SlackAdapter(settings.slack_webhook_url))
    if settings.smtp_host and settings.notification_email_to:
        adapters.append(EmailAdapter(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            sender=settings.notification_email_from or settings.smtp_user or "jobintel@localhost",
            recipients=[r.strip() for r in settings.notification_email_to.split(",") if r.strip()],
            use_tls=settings.smtp_use_tls,
        ))
    return adapters


def urgent_alert_condition(
    overall_score: float,
    age_hours: float,
    geographically_eligible: bool,
    remote_confirmed: bool,
) -> bool:
    """spec §44's urgent-alert condition, with the thresholds read from
    config/profile.yaml rather than hard-coded - "what counts as urgent"
    is a preference, not a constant."""
    alerts = load_profile().get("alerts", {}) or {}
    min_score = float(alerts.get("urgent_min_score", 92))
    max_age = float(alerts.get("urgent_max_age_hours", 24))
    require_eligible = bool(alerts.get("urgent_requires_geographic_eligibility", True))
    require_remote = bool(alerts.get("urgent_requires_confirmed_remote", True))

    if overall_score < min_score or age_hours > max_age:
        return False
    if require_eligible and not geographically_eligible:
        return False
    if require_remote and not remote_confirmed:
        return False
    return True
