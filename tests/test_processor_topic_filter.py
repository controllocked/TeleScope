from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from typing import Optional

from core.config import DedupConfig
from core.models import MatchRecord, MessageContext
from core.processor import MessageProcessor
from core.rules_engine import build_rules


class FakeStorage:
    def __init__(self) -> None:
        self.last_ids: dict[str, int] = {}
        self.saved: list[tuple[MessageContext, MatchRecord]] = []
        self.seen: set[str] = set()

    def get_last_id(self, source_key: str) -> Optional[int]:
        return self.last_ids.get(source_key)

    def set_last_id(self, source_key: str, last_message_id: int) -> None:
        self.last_ids[source_key] = last_message_id

    def is_seen(self, fingerprint: str) -> bool:
        return fingerprint in self.seen

    def mark_seen(self, fingerprint: str) -> None:
        self.seen.add(fingerprint)

    def save_match(self, context: MessageContext, match: MatchRecord) -> None:
        self.saved.append((context, match))


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[MessageContext, str]] = []

    async def send(self, context: MessageContext, match, snippet: str) -> None:
        self.sent.append((context, snippet))


def _make_context(
    *, source_key: str, base_source_key: str, topic_id: Optional[int], message_id: int
) -> MessageContext:
    return MessageContext(
        source_key=source_key,
        base_source_key=base_source_key,
        topic_id=topic_id,
        chat_id=123,
        message_id=message_id,
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        text="hello world",
        permalink=None,
        topic_permalink=None,
    )


def test_allows_base_key_for_topic_message() -> None:
    rules = build_rules([{"name": "greet", "keywords": ["hello"], "enabled": True}])
    storage = FakeStorage()
    notifier = FakeNotifier()
    processor = MessageProcessor(
        rules=rules,
        storage=storage,
        notifier=notifier,
        allowed_sources={"@group"},
        dedup_config=DedupConfig(mode="off", only_on_match=True, ttl_days=30),
        snippet_chars=100,
    )

    context = _make_context(
        source_key="@group#topic:10",
        base_source_key="@group",
        topic_id=10,
        message_id=1,
    )

    asyncio.run(processor.handle(context))

    assert storage.saved
    assert storage.last_ids.get("@group#topic:10") == 1


def test_blocks_other_topics_when_only_topic_key_allowed() -> None:
    rules = build_rules([{"name": "greet", "keywords": ["hello"], "enabled": True}])
    storage = FakeStorage()
    notifier = FakeNotifier()
    processor = MessageProcessor(
        rules=rules,
        storage=storage,
        notifier=notifier,
        allowed_sources={"@group#topic:10"},
        dedup_config=DedupConfig(mode="off", only_on_match=True, ttl_days=30),
        snippet_chars=100,
    )

    context = _make_context(
        source_key="@group#topic:11",
        base_source_key="@group",
        topic_id=11,
        message_id=1,
    )

    asyncio.run(processor.handle(context))

    assert not storage.saved
    assert "@group#topic:11" not in storage.last_ids


def test_idempotency_is_per_effective_key() -> None:
    rules = build_rules([{"name": "greet", "keywords": ["hello"], "enabled": True}])
    storage = FakeStorage()
    notifier = FakeNotifier()
    processor = MessageProcessor(
        rules=rules,
        storage=storage,
        notifier=notifier,
        allowed_sources={"@group"},
        dedup_config=DedupConfig(mode="off", only_on_match=True, ttl_days=30),
        snippet_chars=100,
    )

    context = _make_context(
        source_key="@group#topic:10",
        base_source_key="@group",
        topic_id=10,
        message_id=1,
    )
    asyncio.run(processor.handle(context))

    # Older message in the same topic should be ignored.
    older = _make_context(
        source_key="@group#topic:10",
        base_source_key="@group",
        topic_id=10,
        message_id=1,
    )
    asyncio.run(processor.handle(older))

    assert storage.last_ids["@group#topic:10"] == 1
    assert len(storage.saved) == 1
