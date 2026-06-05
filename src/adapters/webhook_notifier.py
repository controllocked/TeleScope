"""Webhook notification adapter.

Delivers each match as a structured JSON POST to a configurable URL so the
output can be piped into SIEM ingestion endpoints (Splunk HEC, Elastic), chat
webhooks (Slack, Discord), or any custom intake.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from core.models import MessageContext
from core.rules_engine import RuleMatch

LOGGER = logging.getLogger(__name__)


class WebhookNotifier:
    """Notifier adapter that POSTs a JSON payload to a configurable webhook."""

    def __init__(
        self,
        url: str,
        source_aliases: dict[str, str],
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._url = url
        self._source_aliases = source_aliases
        self._headers = headers or {}
        self._timeout = timeout

    def _build_payload(
        self, context: MessageContext, match: RuleMatch, snippet: str
    ) -> dict:
        return {
            "source_key": context.source_key,
            "base_source_key": context.base_source_key,
            "source_alias": self._source_aliases.get(context.source_key)
            or self._source_aliases.get(context.base_source_key),
            "topic_id": context.topic_id,
            "chat_id": context.chat_id,
            "message_id": context.message_id,
            "date": context.date.isoformat() if context.date else None,
            "rule_name": match.rule_name,
            "reason": match.reason,
            "tags": list(match.tags),
            "text_snippet": snippet,
            "text": context.text,
            "permalink": context.permalink,
            "topic_permalink": context.topic_permalink,
        }

    async def send(self, context: MessageContext, match: RuleMatch, snippet: str) -> None:
        """POST the match payload to the configured webhook URL."""

        payload = self._build_payload(context, match, snippet)
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self._url, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        for header_name, header_value in self._headers.items():
            request.add_header(header_name, header_value)

        # A webhook delivery failure never crash the watcher. Log and move on
        # so a misconfigured downstream does not silently stop intelligence flow.
        try:
            with urllib.request.urlopen(request, timeout=self._timeout):
                pass
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            LOGGER.warning("webhook HTTP %s for %s: %s", exc.code, self._url, body[:200])
        except urllib.error.URLError as exc:
            LOGGER.warning("webhook delivery failed for %s: %s", self._url, exc.reason)
        except Exception as exc:  # noqa: BLE001 - never crash the loop on delivery
            LOGGER.warning("webhook unexpected error for %s: %s", self._url, exc)
