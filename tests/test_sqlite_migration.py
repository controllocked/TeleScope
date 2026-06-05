from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from adapters.sqlite_storage import SQLiteStorage
from core.models import MatchRecord, MessageContext


def _legacy_create(db_path: str) -> None:
    """Recreate the pre-tags schema so we can assert migration upgrades it."""

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE matches (
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
        conn.execute(
            "INSERT INTO matches (source_key, chat_id, message_id, date, rule_name, reason, text_snippet, permalink) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "@old",
                1,
                10,
                datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
                "legacy",
                "kw",
                "old snippet",
                "https://t.me/old/10",
            ),
        )


def _ctx() -> MessageContext:
    return MessageContext(
        source_key="@new",
        base_source_key="@new",
        topic_id=None,
        chat_id=2,
        message_id=11,
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        text="text",
        permalink="https://t.me/new/11",
        topic_permalink=None,
    )


def test_init_db_adds_tags_column_to_legacy_db(tmp_path) -> None:
    db_path = tmp_path / "telescope.db"
    _legacy_create(str(db_path))

    storage = SQLiteStorage(str(db_path))
    storage.init_db()

    with sqlite3.connect(str(db_path)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
    assert "tags" in cols

    # Legacy row is preserved with NULL tags
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT source_key, tags FROM matches WHERE source_key = '@old'").fetchall()
    assert len(rows) == 1
    assert rows[0][1] is None


def test_save_match_persists_tags_as_json(tmp_path) -> None:
    db_path = tmp_path / "telescope.db"
    storage = SQLiteStorage(str(db_path))
    storage.init_db()

    storage.save_match(
        _ctx(),
        MatchRecord(
            rule_name="r1",
            reason="kw",
            text_snippet="snip",
            tags=["severity:critical", "category:cve"],
        ),
    )

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT tags FROM matches WHERE source_key = '@new'").fetchone()
    assert row is not None
    import json

    assert json.loads(row[0]) == ["severity:critical", "category:cve"]


def test_save_match_with_empty_tags_stores_null(tmp_path) -> None:
    db_path = tmp_path / "telescope.db"
    storage = SQLiteStorage(str(db_path))
    storage.init_db()

    storage.save_match(
        _ctx(),
        MatchRecord(rule_name="r1", reason="kw", text_snippet="snip", tags=[]),
    )

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT tags FROM matches WHERE source_key = '@new'").fetchone()
    assert row is not None
    assert row[0] is None
