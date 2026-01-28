from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from telethon.tl.types import PeerChannel

from adapters.telegram_mapper import build_context


class DummyChat:
    def __init__(self, username: "str | None" = None) -> None:
        self.username = username


class DummyReply:
    def __init__(
        self,
        forum_topic: bool,
        reply_to_top_id: "int | None",
        reply_to_msg_id: "int | None",
    ) -> None:
        self.forum_topic = forum_topic
        self.reply_to_top_id = reply_to_top_id
        self.reply_to_msg_id = reply_to_msg_id


class DummyMessage:
    def __init__(
        self,
        *,
        chat_id: int,
        message_id: int,
        text: str,
        chat: "DummyChat | None" = None,
        peer_id=None,
        reply_to=None,
    ) -> None:
        self.chat_id = chat_id
        self.id = message_id
        self.raw_text = text
        self.chat = chat
        self.peer_id = peer_id
        self.reply_to = reply_to
        self.date = datetime(2024, 1, 1, tzinfo=timezone.utc)


class DummyResolver:
    def __init__(self, is_forum: bool) -> None:
        self._is_forum = is_forum

    async def is_forum(self, chat_id: int) -> bool:
        return self._is_forum


def test_build_context_topic_id_from_reply_to_top_id() -> None:
    reply_to = DummyReply(forum_topic=True, reply_to_top_id=555, reply_to_msg_id=111)
    message = DummyMessage(
        chat_id=-100123,
        message_id=10,
        text="hello",
        chat=DummyChat(username=None),
        peer_id=PeerChannel(channel_id=123),
        reply_to=reply_to,
    )
    context = asyncio.run(build_context(message, DummyResolver(is_forum=True)))
    assert context.topic_id == 555
    assert context.source_key.endswith("#topic:555")
    assert context.topic_permalink == "https://t.me/c/123/555"


def test_build_context_topic_id_fallback_to_reply_to_msg_id() -> None:
    reply_to = DummyReply(forum_topic=True, reply_to_top_id=None, reply_to_msg_id=777)
    message = DummyMessage(
        chat_id=-100123,
        message_id=10,
        text="hello",
        chat=DummyChat(username=None),
        peer_id=PeerChannel(channel_id=123),
        reply_to=reply_to,
    )
    context = asyncio.run(build_context(message, DummyResolver(is_forum=True)))
    assert context.topic_id == 777
    assert context.source_key.endswith("#topic:777")


def test_build_context_no_forum_topic_flag() -> None:
    message = DummyMessage(
        chat_id=-100123,
        message_id=10,
        text="hello",
        chat=DummyChat(username=None),
        peer_id=PeerChannel(channel_id=123),
        reply_to=None,
    )
    context = asyncio.run(build_context(message, DummyResolver(is_forum=True)))
    assert context.topic_id is None
    assert "#topic:" not in context.source_key
