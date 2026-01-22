"""Telegram Bot API notification adapter.

Uses the Bot API for delivery so notifications can be routed via a bot chat.
"""

from __future__ import annotations

import json
import urllib.request

from adapters.notification_formatting import format_notification
from core.models import MessageContext
from core.rules_engine import RuleMatch


class TelegramBotNotifier:
    """Notifier adapter that sends messages via the Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str, source_aliases: dict[str, str]) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._source_aliases = source_aliases

    def _endpoint(self) -> str:
        # The Bot API endpoint is deterministic and derived from the token.
        return f"https://api.telegram.org/bot{self._bot_token}/sendMessage"

    async def send(self, context: MessageContext, match: RuleMatch, snippet: str) -> None:
        """Send the formatted notification via the Bot API."""

        message = format_notification(match, context, snippet, self._source_aliases, mode="html")
        payload = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._endpoint(), data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        # We use a blocking HTTP call because this is a lightweight MVP; the
        # adapter boundary makes it easy to swap for an async client later.
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Bot API error {e.code}: {body}") from e
