"""Ports (interfaces) used by the core pipeline.

Ports define the minimal contracts for storage and notification adapters so
that the core can be reused with different backends.
"""

from __future__ import annotations

from typing import Optional, Protocol

from core.models import MatchRecord, MessageContext
from core.rules_engine import RuleMatch


class StoragePort(Protocol):
    """Storage operations required by the core pipeline."""

    def get_last_id(self, source_key: str) -> Optional[int]:
        ...

    def set_last_id(self, source_key: str, last_message_id: int) -> None:
        ...

    def is_seen(self, fingerprint: str) -> bool:
        ...

    def mark_seen(self, fingerprint: str) -> None:
        ...

    def save_match(self, context: MessageContext, match: MatchRecord) -> None:
        ...


class NotifierPort(Protocol):
    """Notification operations required by the core pipeline."""

    async def send(self, context: MessageContext, match: RuleMatch, snippet: str) -> None:
        ...
