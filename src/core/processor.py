"""Core message processing pipeline.

This module is integration-agnostic. It only relies on ports for storage and
notifications, enabling future frontends or adapters without changes here.
"""

from __future__ import annotations

import logging
from typing import Iterable

from core.config import DedupConfig
from core.dedup import compute_fingerprint, normalize_for_fingerprint
from core.models import MatchRecord, MessageContext
from core.ports import NotifierPort, StoragePort
from core.rules_engine import Rule, match_rules

LOGGER = logging.getLogger(__name__)


class MessageProcessor:
    """Orchestrates matching, dedup, persistence, and notifications."""

    def __init__(
        self,
        rules: Iterable[Rule],
        storage: StoragePort,
        notifier: NotifierPort,
        allowed_sources: set[str],
        dedup_config: DedupConfig,
        snippet_chars: int,
    ) -> None:
        self._rules = list(rules)
        self._storage = storage
        self._notifier = notifier
        self._allowed_sources = allowed_sources
        self._dedup = dedup_config
        self._snippet_chars = snippet_chars

    async def handle(self, context: MessageContext) -> None:
        """Process one message context through the core pipeline."""

        if context.source_key not in self._allowed_sources:
            return

        # Media-only messages without captions are ignored
        if not context.text.strip():
            return

        # Message-level idempotency: Telegram message ids are monotonically increasing
        # per chat, so we can safely skip anything we've already processed.
        last_id = self._storage.get_last_id(context.source_key) or 0
        if context.message_id <= last_id:
            return
        # Rule evaluation uses the original text for regex accuracy, while keyword
        # checks are case-insensitive inside the rule engine.
        matches = match_rules(context.text, self._rules)
        if not matches:
            self._storage.set_last_id(context.source_key, context.message_id)
            return

        # Content-level dedup is optional and only used when we already have a match.
        # avoids polluting the dedup table with irrelevant messages.
        normalized_text = normalize_for_fingerprint(context.text)
        fingerprint = compute_fingerprint(context.source_key, normalized_text, self._dedup.mode)
        if fingerprint and self._dedup.only_on_match:
            if self._storage.is_seen(fingerprint):
                LOGGER.info("Dedup skip for %s (same message)", context.source_key)
                self._storage.set_last_id(context.source_key, context.message_id)
                return
            self._storage.mark_seen(fingerprint)

        # Snippet is clipped to reduce notification noise and to keep the DB row
        # reasonably small without losing the gist of the match.
        snippet = context.text[: self._snippet_chars].strip()
        for match in matches:
            self._storage.save_match(
                context,
                MatchRecord(
                    rule_name=match.rule_name,
                    reason=match.reason,
                    text_snippet=snippet,
                ),
            )
            await self._notifier.send(context, match, snippet)
            LOGGER.info("Match saved for %s (%s)", context.source_key, match.rule_name)

        # Update the last_message_id after all match handling to ensure restart safety.
        self._storage.set_last_id(context.source_key, context.message_id)
