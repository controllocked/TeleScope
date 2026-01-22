"""Shared notification formatting helpers.

Keeping formatting here prevents drift between adapters and keeps messages
consistent regardless of delivery channel.
"""

from __future__ import annotations

import html

from src.core.models import MessageContext
from src.core.rules_engine import RuleMatch


def format_source_label(source_key: str, source_aliases: dict[str, str]) -> str:
    """Return a human-friendly source label, using configured aliases."""

    alias = source_aliases.get(source_key)
    if not alias:
        return source_key
    return f"{alias} ({source_key})"


def _format_markdown(
    match: RuleMatch,
    context: MessageContext,
    snippet: str,
    source_aliases: dict[str, str],
) -> str:
    """Create the Markdown notification body used by Saved Messages."""

    # Centralized formatting keeps notifications consistent and easy to adjust.
    # Telegram Markdown is supported by passing parse_mode="Markdown".
    def escape_md(value: str) -> str:
        for ch in r"*[`":
            value = value.replace(ch, f"\\{ch}")
        return value

    timestamp = context.date.astimezone().strftime("%H:%M:%S %d-%m-%Y").strip()
    rule_name = escape_md(match.rule_name)
    source = escape_md(format_source_label(context.source_key, source_aliases))
    reason = escape_md(match.reason)
    excerpt = escape_md(snippet)

    divider = "──────────────"

    lines = [
        f"[{timestamp}]",
        f"**Rule:**   {rule_name}",
        f"**Source:** {source}",
        divider,
        "",
        excerpt,
        "",
        "**Why:**",
        reason,
    ]

    if context.permalink:
        lines.extend([
            "",
            "**Link:**",
            context.permalink,
        ])

    lines.append(divider)
    return "\n".join(lines)


def _format_html(
    match: RuleMatch,
    context: MessageContext,
    snippet: str,
    source_aliases: dict[str, str],
) -> str:
    """Create the HTML notification body used by the Bot API adapter."""

    timestamp = html.escape(context.date.astimezone().strftime("%H:%M:%S %d-%m-%Y").strip())
    rule_name = html.escape(match.rule_name)
    source = html.escape(format_source_label(context.source_key, source_aliases))
    reason = html.escape(match.reason)
    excerpt = html.escape(snippet)

    parts = [
        f"[{timestamp}]",
        f"<b>Rule:</b> {rule_name}",
        f"<b>Source:</b> {source}",
        "──────────────",
        "",
        excerpt,
        "",
        "<b>Why:</b>",
        reason,
    ]

    if context.permalink:
        safe_link = html.escape(context.permalink)
        parts.extend(["", "<b>Link:</b>", f"<a href=\"{safe_link}\">{safe_link}</a>"])

    parts.append("──────────────")
    return "\n".join(parts)


def format_notification(
    match: RuleMatch,
    context: MessageContext,
    snippet: str,
    source_aliases: dict[str, str],
    mode: str,
) -> str:
    """Return the notification formatted for the requested mode."""

    if mode == "markdown":
        return _format_markdown(match, context, snippet, source_aliases)
    if mode == "html":
        return _format_html(match, context, snippet, source_aliases)
    raise ValueError(f"Unsupported notification format: {mode}")
