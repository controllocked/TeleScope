from __future__ import annotations

from datetime import datetime, timezone

from adapters.notification_formatting import extract_severity_label, format_notification
from core.models import MessageContext
from core.rules_engine import RuleMatch


def _ctx() -> MessageContext:
    return MessageContext(
        source_key="@chan",
        base_source_key="@chan",
        topic_id=None,
        chat_id=1,
        message_id=42,
        date=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        text="payload",
        permalink="https://t.me/chan/42",
        topic_permalink=None,
    )


def test_extract_severity_label_recognizes_levels() -> None:
    assert extract_severity_label(["severity:critical"]) == "CRITICAL"
    assert extract_severity_label(["severity:high", "category:cve"]) == "HIGH"
    assert extract_severity_label(["category:cve", "severity:low"]) == "LOW"
    assert extract_severity_label(["severity:medium"]) == "MED"
    assert extract_severity_label(["severity:med"]) == "MED"


def test_extract_severity_label_missing_or_unknown() -> None:
    assert extract_severity_label([]) is None
    assert extract_severity_label(["category:cve"]) is None
    assert extract_severity_label(["severity:weird"]) is None


def test_format_notification_adds_severity_prefix_markdown() -> None:
    match = RuleMatch(rule_name="CVE rule", reason="keyword(s): cve", tags=["severity:critical"])
    out = format_notification(match, _ctx(), "snippet", {}, mode="markdown")
    # Markdown escaping puts backslashes before [, so check the literal level
    assert "CRITICAL" in out
    assert "CVE rule" in out
    assert "severity:critical" in out
    assert "Tags:" in out


def test_format_notification_adds_severity_prefix_html() -> None:
    match = RuleMatch(rule_name="0day", reason="kw", tags=["severity:high", "category:0day"])
    out = format_notification(match, _ctx(), "snippet", {}, mode="html")
    assert "[HIGH]" in out
    assert "category:0day" in out


def test_format_notification_no_tags_no_prefix() -> None:
    match = RuleMatch(rule_name="plain", reason="kw", tags=[])
    out = format_notification(match, _ctx(), "snippet", {}, mode="markdown")
    assert "[CRITICAL]" not in out
    assert "[HIGH]" not in out
    assert "Tags:" not in out
