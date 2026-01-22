"""Telegram notification adapter for Saved Messages.

Formats a human-readable Markdown message and sends it to Saved Messages.
"""

from __future__ import annotations

from src.adapters.notification_formatting import format_notification
from src.core.models import MessageContext
from src.core.rules_engine import RuleMatch


class TelegramSavedMessagesNotifier:
    """Notifier adapter that sends messages to the user's Saved Messages."""

    def __init__(self, client, source_aliases: dict[str, str]) -> None:
        self._client = client
        self._source_aliases = source_aliases

    async def send(self, context: MessageContext, match: RuleMatch, snippet: str) -> None:
        """Send the formatted notification to Saved Messages."""

        message = format_notification(match, context, snippet, self._source_aliases, mode="markdown")
        await self._client.send_message("me", message, parse_mode="Markdown")
