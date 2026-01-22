"""Telegram-to-core message mapping adapter.

This keeps Telethon-specific details out of the core pipeline.
"""

from __future__ import annotations

from telethon.tl.custom import Message
from telethon.tl.types import PeerChannel, PeerChat

from core.models import MessageContext


def source_key_from_message(message: Message) -> str:
    """Normalize a source key using a single rule enforced across the app."""

    chat = getattr(message, "chat", None)
    username = getattr(chat, "username", None)

    if isinstance(username, str) and username:
        return f"@{username.lower()}"

    # Fallback: always stable and universal
    return f"chat_id:{message.chat_id}"


def build_context(message: Message) -> MessageContext:
    """Build a core MessageContext from a Telethon Message."""

    source_key = source_key_from_message(message)
    text = message.raw_text or ""

    permalink = None
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

    return MessageContext(
        source_key=source_key,
        chat_id=message.chat_id,
        message_id=message.id,
        date=message.date,
        text=text,
        permalink=permalink,
    )
