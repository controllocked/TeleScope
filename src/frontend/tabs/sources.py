"""Sources tab implementation."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, Switch

from ..modals import AddSourceScreen, DeleteSourceScreen
from ..validators import SourceKeyInfo, parse_source_key


class SourcesTab(Container):
    """Sources tab for editing config.sources."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loading_form = False
        self._current_row_key: Optional[str] = None
        self._table_ready = False

    def compose(self):
        with Vertical(id="sources-panel"):
            with Horizontal(id="sources-body"):
                with Container(id="sources-left"):
                    yield DataTable(id="sources-table", cursor_type="row")
                with Container(id="sources-right"):
                    yield Static("Source details", id="sources-title")
                    yield Static("source_key", classes="form-label")
                    yield Input(placeholder="@channel or chat_id:123", id="source-key-input")
                    yield Static("", id="source-key-error")
                    yield Static("alias", classes="form-label")
                    yield Input(placeholder="Alias", id="alias-input")
                    yield Static("enabled", classes="form-label")
                    yield Switch(value=False, id="enabled-toggle")
                    yield Static("type", classes="form-label")
                    yield Static("", id="source-type")
                    yield Static("topic", classes="form-label")
                    yield Static("", id="source-topic")
            with Horizontal(id="sources-actions"):
                yield Button("Add", id="add-source", variant="success")
                yield Button("Delete", id="delete-source", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        table.add_column("enabled", key="enabled", width=8)
        table.add_column("source_key", key="source_key", width=32)
        table.add_column("alias", key="alias", width=20)
        table.add_column("type", key="type", width=10)
        table.add_column("topic", key="topic", width=12)
        table.zebra_stripes = True
        self._table_ready = True
        self.reload_from_config()
        self._set_form_state(None)

    def reload_from_config(self) -> None:
        if not self._table_ready:
            return
        table = self.query_one("#sources-table", DataTable)
        table.clear()
        for index, source, info in self._iter_sources():
            enabled_label = "yes" if source.get("enabled", True) else "no"
            alias = source.get("alias", "")
            topic_label = f"#topic:{info.topic_id}" if info.topic_id else ""
            row_key = str(index)
            table.add_row(
                enabled_label,
                source.get("source_key", ""),
                alias,
                info.kind,
                topic_label,
                key=row_key,
            )
        self._update_action_state()

    def _iter_sources(self) -> Iterable[tuple[int, dict[str, Any], SourceKeyInfo]]:
        sources = self._get_sources()
        for index, source in enumerate(sources):
            info = parse_source_key(str(source.get("source_key", "")))
            yield index, source, info

    def _get_sources(self) -> list[dict[str, Any]]:
        data = self.app.config_state.data or {}
        sources = data.get("sources")
        if isinstance(sources, list):
            return sources
        return []

    def _set_sources(self, sources: list[dict[str, Any]]) -> None:
        self.app.update_config_section("sources", sources)

    def _update_action_state(self) -> None:
        delete_btn = self.query_one("#delete-source", Button)
        delete_btn.disabled = self._current_row_key is None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._current_row_key = self._coerce_row_key(event.row_key)
        self._set_form_state(self._current_row_key)
        self._update_action_state()

    @on(Input.Changed, "#alias-input")
    def _on_alias_changed(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        sources = self._get_sources()
        if index >= len(sources):
            return
        alias = event.value.strip()
        if alias:
            sources[index]["alias"] = alias
        else:
            sources[index].pop("alias", None)
        self._set_sources(sources)
        self._update_table_cell(index, "alias", alias)

    @on(Input.Changed, "#source-key-input")
    def _on_source_key_changed(self) -> None:
        if self._loading_form:
            return
        self._set_source_key_error("")

    @on(Input.Submitted, "#source-key-input")
    def _on_source_key_submitted(self, event: Input.Submitted) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        sources = self._get_sources()
        if index >= len(sources):
            return
        info = parse_source_key(event.value)
        if info.error or info.normalized is None:
            self._set_source_key_error(info.error or "invalid source_key")
            return
        sources[index]["source_key"] = info.normalized
        self._set_sources(sources)
        self._update_table_cell(index, "source_key", info.normalized)
        self._update_table_cell(index, "type", info.kind)
        topic_label = f"#topic:{info.topic_id}" if info.topic_id else ""
        self._update_table_cell(index, "topic", topic_label)
        self._loading_form = True
        event.input.value = info.normalized
        self._loading_form = False
        self.query_one("#source-type", Static).update(info.kind)
        self.query_one("#source-topic", Static).update(topic_label)

    @on(Switch.Changed, "#enabled-toggle")
    def _on_enabled_changed(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        sources = self._get_sources()
        if index >= len(sources):
            return
        sources[index]["enabled"] = bool(event.value)
        self._set_sources(sources)
        self._update_table_cell(index, "enabled", "yes" if event.value else "no")

    @on(Button.Pressed, "#add-source")
    def _on_add_source(self) -> None:
        self.app.push_screen(AddSourceScreen(), self._handle_add_source)

    @on(Button.Pressed, "#delete-source")
    def _on_delete_source(self) -> None:
        index = self._current_index()
        if index is None:
            return
        sources = self._get_sources()
        if index >= len(sources):
            return
        source_key = str(sources[index].get("source_key", ""))
        self.app.push_screen(DeleteSourceScreen(source_key), self._handle_delete_source)

    def _handle_add_source(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        sources = self._get_sources()
        sources.append(payload)
        self._set_sources(sources)
        self.reload_from_config()

    def _handle_delete_source(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        index = self._current_index()
        if index is None:
            return
        sources = self._get_sources()
        if index >= len(sources):
            return
        sources.pop(index)
        self._set_sources(sources)
        self._current_row_key = None
        self.reload_from_config()
        self._set_form_state(None)

    def _update_table_cell(self, index: int, column_key: str, value: Any) -> None:
        table = self.query_one("#sources-table", DataTable)
        row_key = str(index)
        try:
            table.get_row(row_key)
        except Exception:
            self.reload_from_config()
            return
        table.update_cell(row_key, column_key, value)

    def _set_form_state(self, row_key: Optional[str]) -> None:
        self._loading_form = True
        alias_input = self.query_one("#alias-input", Input)
        enabled_toggle = self.query_one("#enabled-toggle", Switch)
        key_input = self.query_one("#source-key-input", Input)
        type_display = self.query_one("#source-type", Static)
        topic_display = self.query_one("#source-topic", Static)
        self._set_source_key_error("")
        if row_key is None:
            alias_input.value = ""
            alias_input.disabled = True
            enabled_toggle.value = False
            enabled_toggle.disabled = True
            key_input.value = ""
            key_input.disabled = True
            type_display.update("")
            topic_display.update("")
        else:
            index = int(row_key)
            sources = self._get_sources()
            if index >= len(sources):
                self._loading_form = False
                return
            source = sources[index]
            alias_input.value = source.get("alias", "")
            alias_input.disabled = False
            enabled_toggle.value = bool(source.get("enabled", True))
            enabled_toggle.disabled = False
            key_value = str(source.get("source_key", ""))
            key_input.value = key_value
            key_input.disabled = False
            info = parse_source_key(key_value)
            type_display.update(info.kind)
            topic_display.update(f"#topic:{info.topic_id}" if info.topic_id else "")
        self._loading_form = False

    def _current_index(self) -> Optional[int]:
        if self._current_row_key is None:
            return None
        try:
            return int(self._current_row_key)
        except ValueError:
            return None

    @staticmethod
    def _coerce_row_key(value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def _set_source_key_error(self, message: str) -> None:
        error = self.query_one("#source-key-error", Static)
        error.update(message)
