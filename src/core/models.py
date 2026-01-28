"""Core domain models.

These dataclasses are shared across the core and adapters to avoid tight
coupling to any integration-specific types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MessageContext:
    """Minimal message context used by the core processing pipeline."""

    source_key: str
    base_source_key: str
    topic_id: Optional[int]
    chat_id: int
    message_id: int
    date: datetime
    text: str
    permalink: Optional[str]
    topic_permalink: Optional[str]


@dataclass(frozen=True)
class MatchRecord:
    """Persisted representation of a single rule match."""

    rule_name: str
    reason: str
    text_snippet: str
