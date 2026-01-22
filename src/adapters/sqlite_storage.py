"""SQLite storage adapter.

Implements the core StoragePort using a simple SQLite database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.core.models import MatchRecord, MessageContext


class SQLiteStorage:
    """Thin SQLite wrapper that satisfies the StoragePort contract."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables if they do not exist.

        Tables:
        - sources_state: per-source last_message_id for idempotency
        - seen: fingerprints for deduplication (content-level)
        - matches: append-only log of rule matches
        """

        with self._connect() as conn:
            # sources_state keeps a single counter per source so we can safely
            # restart the app without reprocessing old messages.
            # Fields:
            # - source_key: normalized key (PRIMARY KEY)
            # - last_message_id: highest message id processed for that source
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources_state (
                    source_key TEXT PRIMARY KEY,
                    last_message_id INTEGER NOT NULL
                )
                """
            )
            # seen stores content fingerprints to avoid alerting on repeated
            # messages. This is optional and only used for matched content.
            # Fields:
            # - fingerprint: SHA-256 hash of normalized content (PRIMARY KEY)
            # - first_seen: timestamp of first observation for TTL cleanup
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen (
                    fingerprint TEXT PRIMARY KEY,
                    first_seen TIMESTAMP NOT NULL
                )
                """
            )
            # matches is an append-only log for auditing. We keep it denormalized
            # for simplicity and to avoid costly joins in the MVP.
            # Fields:
            # - id: auto-increment primary key
            # - source_key: normalized source string used for filtering
            # - chat_id: raw Telegram chat id for debugging/reference
            # - message_id: message id within the chat for idempotency tracing
            # - date: original message timestamp from Telegram
            # - rule_name: name of the rule that matched
            # - reason: human-readable match explanation (keywords/regex)
            # - text_snippet: clipped portion of the message text
            # - permalink: t.me link
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_key TEXT,
                    chat_id INTEGER,
                    message_id INTEGER,
                    date TIMESTAMP,
                    rule_name TEXT,
                    reason TEXT,
                    text_snippet TEXT,
                    permalink TEXT
                )
                """
            )

    def get_last_id(self, source_key: str) -> Optional[int]:
        """Return the last processed message_id for a source, if any."""

        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_message_id FROM sources_state WHERE source_key = ?",
                (source_key,),
            ).fetchone()
        return int(row["last_message_id"]) if row else None

    def set_last_id(self, source_key: str, last_message_id: int) -> None:
        """Upsert the last processed message_id for a source."""

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sources_state (source_key, last_message_id)
                VALUES (?, ?)
                ON CONFLICT(source_key) DO UPDATE SET last_message_id = excluded.last_message_id
                """,
                (source_key, last_message_id),
            )

    def is_seen(self, fingerprint: str) -> bool:
        """Check if a fingerprint has already been recorded."""

        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return row is not None

    def mark_seen(self, fingerprint: str) -> None:
        """Insert a fingerprint if it does not exist."""

        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO seen (fingerprint, first_seen)
                VALUES (?, ?)
                """,
                (fingerprint, now.isoformat()),
            )

    def save_match(self, context: MessageContext, match: MatchRecord) -> None:
        """Persist a match to the append-only matches table."""

        created_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO matches (
                    source_key,
                    chat_id,
                    message_id,
                    date,
                    rule_name,
                    reason,
                    text_snippet,
                    permalink
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.source_key,
                    context.chat_id,
                    context.message_id,
                    context.date.isoformat(),
                    match.rule_name,
                    match.reason,
                    match.text_snippet,
                    context.permalink
                ),
            )

    def cleanup_seen(self, ttl_days: int) -> int:
        """Delete old fingerprints and return the number removed."""

        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM seen WHERE first_seen < ?",
                (cutoff.isoformat(),),
            )
            return cur.rowcount

    def list_sources_state(self) -> set[str]:
        """Return all source_key values currently tracked in sources_state."""

        with self._connect() as conn:
            rows = conn.execute("SELECT source_key FROM sources_state").fetchall()
        return {row["source_key"] for row in rows}
