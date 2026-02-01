"""Data tab for viewing and exporting match history."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Static

from ..constants import PROJECT_ROOT


class DataTab(Container):
    """Data tab to browse matches and export to JSON/CSV."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._rows: list[dict[str, Any]] = []
        self._table_ready = False

    def compose(self):
        with Vertical(id="data-panel"):
            yield Static("Matches", id="data-title")
            yield DataTable(id="data-table", cursor_type="row")
            with Horizontal(id="data-actions"):
                yield Button("Export JSON", id="export-json", variant="success")
                yield Button("Export CSV", id="export-csv")
            yield Static("", id="data-output")

    def on_mount(self) -> None:
        table = self.query_one("#data-table", DataTable)
        table.add_column("date", key="date", width=18)
        table.add_column("source", key="source_key", width=18)
        table.add_column("rule", key="rule_name", width=20)
        table.add_column("snippet", key="text_snippet", width=42)
        table.zebra_stripes = True
        table.styles.height = "1fr"
        self.query_one("#data-actions").styles.height = 3
        self._table_ready = True
        self._load_matches()

    @property
    def _db_path(self) -> Path:
        return PROJECT_ROOT / "src" / "telescope.db"

    @on(Button.Pressed, "#export-json")
    def _on_export_json(self) -> None:
        self._export_rows("json")

    @on(Button.Pressed, "#export-csv")
    def _on_export_csv(self) -> None:
        self._export_rows("csv")

    def _load_matches(self) -> None:
        if not self._table_ready:
            return
        table = self.query_one("#data-table", DataTable)
        table.clear()
        db_path = self._db_path
        if not db_path.exists():
            self._rows = []
            self._set_output(f"db not found: {db_path}")
            return
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, source_key, chat_id, message_id, date, rule_name,
                           reason, text_snippet, permalink
                    FROM matches
                    ORDER BY date DESC
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            self._rows = []
            self._set_output(f"db error: {exc}")
            return

        self._rows = [dict(row) for row in rows]
        for row in rows:
            table.add_row(
                self._format_date_display(row["date"]),
                row["source_key"] or "",
                row["rule_name"] or "",
                self._clip_text(row["text_snippet"] or ""),
                key=str(row["id"]),
            )
        self._set_output(f"loaded {len(rows)} matches from {db_path}")

    def _export_rows(self, fmt: str) -> None:
        if not self._rows:
            self._set_output("No matches to export.")
            return
        exports_dir = PROJECT_ROOT / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = exports_dir / f"matches-{timestamp}.{fmt}"
        try:
            if fmt == "json":
                path.write_text(json.dumps(self._rows, indent=2, ensure_ascii=True), encoding="utf-8")
            else:
                fieldnames = list(self._rows[0].keys())
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self._rows)
            self._set_output(f"exported {len(self._rows)} matches to {path}")
        except OSError as exc:
            self._set_output(f"export failed: {exc.strerror or exc}")

    def _set_output(self, message: str) -> None:
        self.query_one("#data-output", Static).update(message)

    @staticmethod
    def _clip_text(value: str, limit: int = 64) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    @staticmethod
    def _format_date_display(value: str) -> str:
        if not value:
            return ""
        display = value.replace("T", " ")
        return display[:19]
