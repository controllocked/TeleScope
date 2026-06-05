from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

from adapters.webhook_notifier import WebhookNotifier
from core.models import MessageContext
from core.rules_engine import RuleMatch


def _ctx() -> MessageContext:
    return MessageContext(
        source_key="@chan",
        base_source_key="@chan",
        topic_id=None,
        chat_id=42,
        message_id=7,
        date=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        text="full message text",
        permalink="https://t.me/chan/7",
        topic_permalink=None,
    )


def _match(tags: Optional[list[str]] = None) -> RuleMatch:
    return RuleMatch(rule_name="r1", reason="kw: foo", tags=tags or [])


def test_webhook_posts_json_payload_with_expected_fields() -> None:
    notifier = WebhookNotifier(
        url="https://example.test/hook",
        source_aliases={"@chan": "Channel Alias"},
        headers={"X-Auth": "secret"},
        timeout=2.5,
    )
    match = _match(tags=["severity:high", "category:cve"])

    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["data"] = request.data
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        return _FakeResp()

    with patch("adapters.webhook_notifier.urllib.request.urlopen", side_effect=_fake_urlopen):
        asyncio.run(notifier.send(_ctx(), match, "snippet here"))

    assert captured["url"] == "https://example.test/hook"
    assert captured["timeout"] == 2.5
    # Headers may be title-cased by urllib; check case-insensitively
    headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lower.get("content-type") == "application/json"
    assert headers_lower.get("x-auth") == "secret"

    payload = json.loads(captured["data"].decode("utf-8"))
    assert payload["source_key"] == "@chan"
    assert payload["source_alias"] == "Channel Alias"
    assert payload["chat_id"] == 42
    assert payload["message_id"] == 7
    assert payload["rule_name"] == "r1"
    assert payload["tags"] == ["severity:high", "category:cve"]
    assert payload["text_snippet"] == "snippet here"
    assert payload["text"] == "full message text"
    assert payload["permalink"] == "https://t.me/chan/7"


def test_webhook_swallows_http_errors() -> None:
    import urllib.error

    notifier = WebhookNotifier(url="https://example.test/hook", source_aliases={})

    def _raise(*_args, **_kwargs):
        raise urllib.error.URLError("connection refused")

    with patch("adapters.webhook_notifier.urllib.request.urlopen", side_effect=_raise):
        # Must not raise - webhook delivery failures should not crash the watcher.
        asyncio.run(notifier.send(_ctx(), _match(), "x"))
