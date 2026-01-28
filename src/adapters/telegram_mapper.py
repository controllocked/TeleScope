"""Telegram-to-core message mapping adapter.

This keeps Telethon-specific details out of the core pipeline.
"""

from __future__ import annotations

from typing import Optional

from telethon.tl.custom import Message
from telethon.tl.types import PeerChannel, PeerChat

from core.models import MessageContext
from core.source_keys import build_effective_source_key


class ForumResolver:
    """Resolve whether a chat is forum-enabled, with a chat_id cache."""

    def __init__(self, client) -> None:
        self._client = client
        self._cache: dict[int, bool] = {}

    async def is_forum(self, chat_id: int) -> bool:
        if chat_id in self._cache:
            return self._cache[chat_id]
        try:
            entity = await self._client.get_entity(chat_id)
        except Exception:
            self._cache[chat_id] = False
            return False
        is_forum = bool(getattr(entity, "forum", False))
        self._cache[chat_id] = is_forum
        return is_forum


def source_key_from_message(message: Message) -> str:
    """Normalize a source key using a single rule enforced across the app."""

    chat = getattr(message, "chat", None)
    username = getattr(chat, "username", None)

    if isinstance(username, str) and username:
        return f"@{username.lower()}"

    # Fallback: always stable and universal
    return f"chat_id:{message.chat_id}"


def _topic_id_from_message(message: Message) -> Optional[int]:
    reply_to = getattr(message, "reply_to", None)
    if not reply_to or not getattr(reply_to, "forum_topic", False):
        return None
    top_id = getattr(reply_to, "reply_to_top_id", None)
    if top_id:
        return top_id
    return getattr(reply_to, "reply_to_msg_id", None)


def _build_topic_permalink(message: Message, topic_id: int) -> Optional[str]:
    if message.chat and getattr(message.chat, "username", None):
        return f"https://t.me/{message.chat.username}/{topic_id}"

    peer_id = message.peer_id
    if not peer_id:
        return None
    if isinstance(peer_id, PeerChannel):
        return f"https://t.me/c/{peer_id.channel_id}/{topic_id}"
    if isinstance(peer_id, PeerChat):
        return f"https://t.me/c/{peer_id.chat_id}/{topic_id}"
    return None


async def build_context(message: Message, forum_resolver: Optional[ForumResolver] = None) -> MessageContext:
    """Build a core MessageContext from a Telethon Message."""

    base_source_key = source_key_from_message(message)
    topic_id = _topic_id_from_message(message)
    if topic_id is None and forum_resolver is not None:
        # Determine if the chat is forum-enabled to distinguish "General" from non-forum chats.
        is_forum_chat = await forum_resolver.is_forum(message.chat_id)
        if is_forum_chat:
            topic_id = None
    effective_source_key = build_effective_source_key(base_source_key, topic_id)
    text = message.raw_text or ""

    permalink = None
    topic_permalink = None
    peer_id = message.peer_id
    # Prefer public usernames for permalinks when available.
    if message.chat and getattr(message.chat, "username", None):
        permalink = f"https://t.me/{message.chat.username}/{message.id}"
    elif peer_id:
        # Private groups/supergroups/channels can use the /c/ links.
        if isinstance(peer_id, PeerChannel):
            permalink = f"https://t.me/c/{peer_id.channel_id}/{message.id}"
        elif isinstance(peer_id, PeerChat):
            permalink = f"https://t.me/c/{peer_id.chat_id}/{message.id}"
        # PeerUser has no chat/channel id; no permalink is possible.

    if topic_id is not None:
        topic_permalink = _build_topic_permalink(message, topic_id)

    return MessageContext(
        source_key=effective_source_key,
        base_source_key=base_source_key,
        topic_id=topic_id,
        chat_id=message.chat_id,
        message_id=message.id,
        date=message.date,
        text=text,
        permalink=permalink,
        topic_permalink=topic_permalink,
    )
