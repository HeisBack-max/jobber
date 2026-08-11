"""Optional alert adapters (spec §44). None are required for MVP
operation - every adapter is disabled unless its configuration is
present in the environment, and `get_enabled_adapters()` simply returns
an empty list when nothing is configured."""

from __future__ import annotations

from abc import ABC, abstractmethod

from jobintel.settings import get_settings


class NotificationAdapter(ABC):
    name: str

    @abstractmethod
    async def send(self, subject: str, body: str) -> None: ...


class TelegramAdapter(NotificationAdapter):
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def send(self, subject: str, body: str) -> None:
        import httpx

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": self._chat_id, "text": f"{subject}\n\n{body}"})


class SlackAdapter(NotificationAdapter):
    name = "slack"

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def send(self, subject: str, body: str) -> None:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(self._webhook_url, json={"text": f"*{subject}*\n{body}"})


def get_enabled_adapters() -> list[NotificationAdapter]:
    settings = get_settings()
    adapters: list[NotificationAdapter] = []
    if settings.telegram_bot_token and settings.telegram_chat_id:
        adapters.append(TelegramAdapter(settings.telegram_bot_token, settings.telegram_chat_id))
    if settings.slack_webhook_url:
        adapters.append(SlackAdapter(settings.slack_webhook_url))
    return adapters


def urgent_alert_condition(overall_score: float, age_hours: float, geographically_eligible: bool, remote_confirmed: bool) -> bool:
    """spec §44 example urgent-alert condition."""
    return overall_score >= 92 and age_hours <= 24 and geographically_eligible and remote_confirmed
