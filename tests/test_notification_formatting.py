from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from adapters.notification_formatting import format_source_label
from core.models import MessageContext


def _context(
    *,
    source_key: str,
    base_source_key: str,
    topic_id: Optional[int],
) -> MessageContext:
    return MessageContext(
        source_key=source_key,
        base_source_key=base_source_key,
        topic_id=topic_id,
        chat_id=1,
        message_id=1,
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        text="hello",
        permalink=None,
        topic_permalink=None,
    )


def test_format_source_label_with_topic_alias() -> None:
    context = _context(
        source_key="@team#topic:10",
        base_source_key="@team",
        topic_id=10,
    )
    aliases = {"@team": "Team", "@team#topic:10": "Hiring"}
    label = format_source_label(context, aliases)
    assert "Team / Hiring" in label
    assert "@team#topic:10" in label


def test_format_source_label_with_base_only_alias() -> None:
    context = _context(
        source_key="@team#topic:11",
        base_source_key="@team",
        topic_id=11,
    )
    aliases = {"@team": "Team"}
    label = format_source_label(context, aliases)
    assert label.startswith("Team / topic 11")
