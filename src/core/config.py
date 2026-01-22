"""Core configuration dataclasses.

We keep config parsing outside the core, but these dataclasses define the
shape the core expects so adapters and app layers can build safely.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DedupConfig:
    """Deduplication settings for the core pipeline."""

    mode: str
    only_on_match: bool
    ttl_days: int


@dataclass(frozen=True)
class NotificationConfig:
    """Notification formatting settings consumed by notifier adapters."""

    snippet_chars: int
