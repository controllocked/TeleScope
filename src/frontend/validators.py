"""Validation helpers for config editing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceKeyInfo:
    normalized: str | None
    kind: str
    topic_id: str | None
    error: str | None = None


def parse_source_key(raw_value: str) -> SourceKeyInfo:
    raw_value = raw_value.strip()
    if not raw_value:
        return SourceKeyInfo(None, "invalid", None, "source_key is required")

    base, sep, topic = raw_value.partition("#topic:")
    topic_id: str | None = None
    if sep:
        if not topic.isdigit():
            return SourceKeyInfo(None, "invalid", None, "topic id must be numeric")
        topic_id = topic

    if base.startswith("@"):
        username = base[1:]
        if not username or not username.replace("_", "a").isalnum():
            return SourceKeyInfo(None, "invalid", topic_id, "username is invalid")
        normalized = f"@{username.lower()}"
        if topic_id:
            normalized = f"{normalized}#topic:{topic_id}"
        return SourceKeyInfo(normalized, "username", topic_id)

    if base.startswith("chat_id:"):
        chat_value = base[len("chat_id:") :]
        if not chat_value or not _is_int(chat_value):
            return SourceKeyInfo(None, "invalid", topic_id, "chat_id must be numeric")
        normalized = f"chat_id:{int(chat_value)}"
        if topic_id:
            normalized = f"{normalized}#topic:{topic_id}"
        return SourceKeyInfo(normalized, "chat_id", topic_id)

    return SourceKeyInfo(None, "invalid", None, "source_key must start with @ or chat_id:")


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True
