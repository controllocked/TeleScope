"""Helpers for working with telescope source keys."""

from __future__ import annotations

from typing import Optional, Tuple

TOPIC_SUFFIX = "#topic:"


def build_effective_source_key(base_source_key: str, topic_id: Optional[int]) -> str:
    """Return the effective key, adding a topic suffix when needed."""

    if topic_id is None:
        return base_source_key
    return f"{base_source_key}{TOPIC_SUFFIX}{topic_id}"


def split_source_key(source_key: str) -> Tuple[str, Optional[int]]:
    """Split a source key into (base_key, topic_id)."""

    if TOPIC_SUFFIX not in source_key:
        return source_key, None
    base_key, _, topic_part = source_key.partition(TOPIC_SUFFIX)
    if not base_key:
        return source_key, None
    try:
        return base_key, int(topic_part)
    except ValueError:
        return source_key, None


def _expand_chat_id_variants(raw_chat_id: int) -> set[int]:
    """Return equivalent chat id variants (peer id, chat id, channel id)."""

    variants: set[int] = {raw_chat_id}
    if raw_chat_id < 0:
        raw_text = str(raw_chat_id)
        if raw_text.startswith("-100"):
            # Channel/supergroup peer id: -100<channel_id>
            channel_part = raw_text[4:]
            if channel_part.isdigit():
                variants.add(int(channel_part))
        else:
            variants.add(abs(raw_chat_id))
        return variants

    # raw_chat_id is positive: add PeerChat and PeerChannel-style ids.
    variants.add(-raw_chat_id)
    variants.add(-1000000000000 - raw_chat_id)
    return variants


def expand_source_key_variants(source_key: str) -> set[str]:
    """Expand a source key to include equivalent chat_id variants."""

    base_key, topic_id = split_source_key(source_key)
    if base_key.startswith("@"):
        return {source_key}
    if not base_key.startswith("chat_id:"):
        return {source_key}

    try:
        raw_chat_id = int(base_key.split("chat_id:", 1)[1])
    except ValueError:
        return {source_key}

    base_keys = {f"chat_id:{variant}" for variant in _expand_chat_id_variants(raw_chat_id)}
    if topic_id is None:
        return base_keys
    return {build_effective_source_key(base_key_item, topic_id) for base_key_item in base_keys}
