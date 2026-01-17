"""Processing pipeline for incoming Telegram messages.

The pipeline enforces a strict order:
1) Build MessageContext from the Telethon event
2) Fast-exit for untracked sources or empty text
3) Message-level idempotency (per source)
4) Apply rules
5) Optional content-level deduplication
6) Persist matches + notify Saved Messages
7) Update per-source last_message_id

This design favors correctness and restart-safety over micro-optimizations.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterable, Optional

from telethon.tl.custom import Message

import settings
from rules import Rule, RuleMatch, match_rules
from storage import MatchRecord, MessageContext, Storage

LOGGER = logging.getLogger(__name__)


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_fingerprint(text: str) -> str:
    """Normalize text for deterministic fingerprinting."""

    return _collapse_whitespace(text).lower()


def compute_fingerprint(source_key: str, normalized_text: str) -> Optional[str]:
    """Return a fingerprint hash based on dedup mode."""

    mode = settings.DEDUP_MODE
    if mode == "off":
        return None

    if mode == "global":
        payload = normalized_text
    elif mode == "per_source":
        payload = f"{source_key}\n{normalized_text}"
    else:
        raise ValueError(f"Unsupported DEDUP_MODE: {mode}")

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_key_from_message(message: Message) -> str:
    """Normalize a source key using the single rule enforced across the app."""

    username = None
    if message.chat and message.chat.username:
        username = message.chat.username.lower()

    if username:
        return f"@{username}"

    return f"chat_id:{message.chat_id}"


def build_context(message: Message) -> MessageContext:
    """Build a MessageContext from Telethon's Message object."""

    source_key = source_key_from_message(message)
    text = message.raw_text or ""

    permalink = None
    if message.chat and message.chat.username:
        permalink = f"https://t.me/{message.chat.username}/{message.id}"

    return MessageContext(
        source_key=source_key,
        chat_id=message.chat_id,
        message_id=message.id,
        date=message.date,
        text=text,
        permalink=permalink,
    )


def _format_notification(match: RuleMatch, context: MessageContext, snippet: str) -> str:
    # Centralized formatting keeps notifications consistent and easy to adjust.
    # Telegram Markdown is supported by passing parse_mode="md" when sending.
    def escape_md(value: str) -> str:
        for ch in ("*", "_", "`", "["):
            value = value.replace(ch, f"\\{ch}")
        return value

    timestamp = context.date.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    reason = escape_md(match.reason)
    source = escape_md(context.source_key)
    rule_name = escape_md(match.rule_name)
    excerpt = escape_md(snippet)

    lines = [
        timestamp,
        f"**Rule:** {rule_name}",
        f"**Source:** {source}",
        f"**Reason:** {reason}",
        "**Excerpt:**",
        excerpt,
    ]
    if context.permalink:
        lines.append(f"**Permalink:** {context.permalink}")
    return "\n".join(lines)


async def process_message(
    storage: Storage,
    client,
    rules: Iterable[Rule],
    message: Message,
) -> None:
    """Run the strict processing pipeline for one incoming message."""

    context = build_context(message)

    # Fast exits keep hot paths cheap and reduce DB writes for irrelevant events.
    if context.source_key not in settings.SOURCES:
        return

    # Media-only messages without captions are ignored because the MVP only
    # matches on text. This avoids false positives on stickers or attachments.
    if not context.text.strip():
        return

    # Message-level idempotency: Telegram message ids are monotonically increasing
    # per chat, so we can safely skip anything we've already processed.
    last_id = storage.get_last_id(context.source_key) or 0
    if context.message_id <= last_id:
        return

    # Rule evaluation uses the original text for regex fidelity, while keyword
    # checks are case-insensitive inside the rule engine.
    matches = match_rules(context.text, rules)
    if not matches:
        storage.set_last_id(context.source_key, context.message_id)
        return

    # Content-level dedup is optional and only used when we already have a match.
    # This avoids polluting the dedup table with irrelevant messages.
    normalized_text = normalize_for_fingerprint(context.text)
    fingerprint = compute_fingerprint(context.source_key, normalized_text)
    if fingerprint and settings.DEDUP_ONLY_ON_MATCH:
        if storage.is_seen(fingerprint):
            LOGGER.info("Dedup skip for %s", context.source_key)
            storage.set_last_id(context.source_key, context.message_id)
            return
        storage.mark_seen(fingerprint)

    # Snippet is clipped to reduce notification noise and to keep the DB row
    # reasonably small without losing the gist of the match.
    snippet = context.text[: settings.SNIPPET_CHARS].strip()
    for match in matches:
        storage.save_match(
            context,
            MatchRecord(
                rule_name=match.rule_name,
                reason=match.reason,
                text_snippet=snippet,
            ),
        )
        notification = _format_notification(match, context, snippet)
        await client.send_message("me", notification, parse_mode="md")
        LOGGER.info("Match saved for %s (%s)", context.source_key, match.rule_name)

    # Update the last_message_id after all match handling to ensure restart safety.
    storage.set_last_id(context.source_key, context.message_id)
