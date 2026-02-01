"""Settings tab implementation."""

from __future__ import annotations

from typing import Any, Optional

from textual import on
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import ContentSwitcher, DataTable, Input, Select, Static, Switch, TextArea


class SettingsTab(Container):
    """Settings tab for editing dedup, notifications, logging, and catch-up."""

    DEDUP_MODES = ["off", "per_source", "global"]
    NOTIFICATION_METHODS = ["saved_messages", "bot"]
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

    SECTION_LABELS = [
        ("dedup", "Dedup", "Duplicate suppression and TTL"),
        ("notifications", "Notifications", "Delivery method and snippets"),
        ("logging", "Logging", "Console/file logging + redaction"),
        ("catch_up", "Catch-up", "Startup backfill scan"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loading_form = False
        self._current_section: Optional[str] = None
        self._table_ready = False

    def compose(self):
        with Vertical(id="settings-panel"):
            with Horizontal(id="settings-body"):
                with Container(id="settings-left"):
                    yield DataTable(id="settings-table", cursor_type="row")
                with Container(id="settings-right"):
                    with ContentSwitcher(id="settings-forms"):
                        with Container(id="settings-dedup"):
                            yield Static("Dedup", id="settings-title")
                            yield Static("mode", classes="form-label")
                            yield Select(
                                [
                                    ("off", "off"),
                                    ("per_source", "per_source"),
                                    ("global", "global"),
                                ],
                                id="dedup-mode",
                                allow_blank=False,
                            )
                            yield Static("only_on_match", classes="form-label")
                            yield Switch(id="dedup-only-on-match")
                            yield Static("ttl_days", classes="form-label")
                            yield Input(placeholder="30", id="dedup-ttl-days")
                            yield Static("", id="dedup-error", classes="settings-error")

                        with Container(id="settings-notifications"):
                            yield Static("Notifications", id="settings-title")
                            yield Static("notification_method", classes="form-label")
                            yield Select(
                                [
                                    ("saved_messages", "saved_messages"),
                                    ("bot", "bot"),
                                ],
                                id="notifications-method",
                                allow_blank=False,
                            )
                            yield Static("snippet_chars", classes="form-label")
                            yield Input(placeholder="400", id="notifications-snippet")
                            yield Static("bot_chat_id", classes="form-label")
                            yield Input(placeholder="123456789", id="notifications-bot")
                            yield Static("", id="notifications-error", classes="settings-error")

                        with ScrollableContainer(id="settings-logging"):
                            yield Static("Logging", id="settings-title")
                            yield Static("enabled", classes="form-label")
                            yield Switch(id="logging-enabled")
                            yield Static("level", classes="form-label")
                            yield Select(
                                [
                                    ("DEBUG", "DEBUG"),
                                    ("INFO", "INFO"),
                                    ("WARNING", "WARNING"),
                                    ("ERROR", "ERROR"),
                                ],
                                id="logging-level",
                                allow_blank=False,
                            )
                            yield Static("console", classes="form-label")
                            yield Switch(id="logging-console")
                            yield Static("file.enabled", classes="form-label")
                            yield Switch(id="logging-file-enabled")
                            yield Static("file.path", classes="form-label")
                            yield Input(placeholder="logs/telescope.log", id="logging-file-path")
                            yield Static("file.max_bytes", classes="form-label")
                            yield Input(placeholder="5242880", id="logging-file-max-bytes")
                            yield Static("file.backup_count", classes="form-label")
                            yield Input(placeholder="5", id="logging-file-backup")
                            yield Static("redact.enabled", classes="form-label")
                            yield Switch(id="logging-redact-enabled")
                            yield Static("redact.patterns (one per line)", classes="form-label")
                            yield TextArea(id="logging-redact-patterns")
                            yield Static("", id="logging-error", classes="settings-error")

                        with Container(id="settings-catch-up"):
                            yield Static("Catch-up", id="settings-title")
                            yield Static("enabled", classes="form-label")
                            yield Switch(id="catchup-enabled")
                            yield Static("messages_per_source", classes="form-label")
                            yield Input(placeholder="50", id="catchup-messages")
                            yield Static("", id="catchup-error", classes="settings-error")

    def on_mount(self) -> None:
        table = self.query_one("#settings-table", DataTable)
        table.add_column("section", key="section", width=18)
        table.add_column("description", key="description", width=34)
        for key, label, description in self.SECTION_LABELS:
            table.add_row(label, description, key=key)
        table.zebra_stripes = True
        self._table_ready = True
        self._select_section("dedup")
        self.reload_from_config()

    def reload_from_config(self) -> None:
        self._loading_form = True
        self._load_dedup()
        self._load_notifications()
        self._load_logging()
        self._load_catch_up()
        self._loading_form = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        section_id = self._coerce_row_key(event.row_key)
        self._select_section(section_id)

    def _select_section(self, section_id: str) -> None:
        self._current_section = section_id
        switcher = self.query_one("#settings-forms", ContentSwitcher)
        switcher.current = f"settings-{section_id.replace('_', '-')}"
        table = self.query_one("#settings-table", DataTable)
        try:
            table.cursor_row = section_id
        except Exception:
            pass

    def _get_section(self, key: str) -> dict[str, Any]:
        data = self.app.config_state.data or {}
        section = data.get(key)
        if isinstance(section, dict):
            return section
        return {}

    def _update_section(self, key: str, section: dict[str, Any]) -> None:
        self.app.update_config_section(key, section)

    def _load_dedup(self) -> None:
        dedup = self._get_section("dedup")
        mode = dedup.get("mode", "per_source")
        only_on_match = bool(dedup.get("only_on_match", True))
        ttl_days = dedup.get("ttl_days", 30)
        self._set_select_value("#dedup-mode", mode, self.DEDUP_MODES, "dedup-error")
        self.query_one("#dedup-only-on-match", Switch).value = only_on_match
        self.query_one("#dedup-ttl-days", Input).value = str(ttl_days)
        self._set_error("dedup-error", "")

    def _load_notifications(self) -> None:
        notifications = self._get_section("notifications")
        method = notifications.get("notification_method", "saved_messages")
        snippet_chars = notifications.get("snippet_chars", 400)
        bot_chat_id = notifications.get("bot_chat_id")
        self._set_select_value(
            "#notifications-method",
            method,
            self.NOTIFICATION_METHODS,
            "notifications-error",
        )
        self.query_one("#notifications-snippet", Input).value = str(snippet_chars)
        self.query_one("#notifications-bot", Input).value = "" if bot_chat_id is None else str(bot_chat_id)
        self._apply_notifications_state(method)
        self._set_error("notifications-error", "")

    def _load_logging(self) -> None:
        logging = self._get_section("logging")
        file_cfg = self._get_subdict(logging, "file")
        redact_cfg = self._get_subdict(logging, "redact")
        enabled = bool(logging.get("enabled", False))
        level = logging.get("level", "INFO")
        console = bool(logging.get("console", True))
        file_enabled = bool(file_cfg.get("enabled", False))
        file_path = file_cfg.get("path", "logs/telescope.log")
        file_max = file_cfg.get("max_bytes", 5 * 1024 * 1024)
        file_backup = file_cfg.get("backup_count", 5)
        redact_enabled = bool(redact_cfg.get("enabled", False))
        patterns = redact_cfg.get("patterns", []) or []

        self.query_one("#logging-enabled", Switch).value = enabled
        self._set_select_value("#logging-level", level, self.LOG_LEVELS, "logging-error")
        self.query_one("#logging-console", Switch).value = console
        self.query_one("#logging-file-enabled", Switch).value = file_enabled
        self.query_one("#logging-file-path", Input).value = str(file_path)
        self.query_one("#logging-file-max-bytes", Input).value = str(file_max)
        self.query_one("#logging-file-backup", Input).value = str(file_backup)
        self.query_one("#logging-redact-enabled", Switch).value = redact_enabled
        self.query_one("#logging-redact-patterns", TextArea).text = "\n".join(patterns)
        self._apply_logging_state(file_enabled, redact_enabled)
        self._set_error("logging-error", "")

    def _load_catch_up(self) -> None:
        catch_up = self._get_section("catch_up")
        enabled = bool(catch_up.get("enabled", False))
        messages = catch_up.get("messages_per_source", 50)
        self.query_one("#catchup-enabled", Switch).value = enabled
        self.query_one("#catchup-messages", Input).value = str(messages)
        self._set_error("catchup-error", "")

    def _set_select_value(self, selector: str, value: str, allowed: list[str], error_id: str) -> None:
        select = self.query_one(selector, Select)
        if value in allowed:
            select.value = value
            self._set_error(error_id, "")
        else:
            select.value = allowed[0] if allowed else Select.BLANK
            self._set_error(error_id, f"Invalid value: {value}")

    def _set_error(self, error_id: str, message: str) -> None:
        self.query_one(f"#{error_id}", Static).update(message)

    def _apply_notifications_state(self, method: str) -> None:
        bot_input = self.query_one("#notifications-bot", Input)
        bot_input.disabled = method != "bot"

    def _apply_logging_state(self, file_enabled: bool, redact_enabled: bool) -> None:
        self.query_one("#logging-file-path", Input).disabled = not file_enabled
        self.query_one("#logging-file-max-bytes", Input).disabled = not file_enabled
        self.query_one("#logging-file-backup", Input).disabled = not file_enabled
        self.query_one("#logging-redact-patterns", TextArea).disabled = not redact_enabled

    @on(Select.Changed, "#dedup-mode")
    def _on_dedup_mode_changed(self, event: Select.Changed) -> None:
        if self._loading_form or event.value is Select.BLANK:
            return
        dedup = self._get_section("dedup")
        dedup["mode"] = event.value
        self._update_section("dedup", dedup)

    @on(Switch.Changed, "#dedup-only-on-match")
    def _on_dedup_only_on_match(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        dedup = self._get_section("dedup")
        dedup["only_on_match"] = bool(event.value)
        self._update_section("dedup", dedup)

    @on(Input.Changed, "#dedup-ttl-days")
    def _on_dedup_ttl_changed(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        self._update_int_field("dedup", "ttl_days", event.value, "dedup-error")

    @on(Select.Changed, "#notifications-method")
    def _on_notifications_method(self, event: Select.Changed) -> None:
        if self._loading_form or event.value is Select.BLANK:
            return
        notifications = self._get_section("notifications")
        notifications["notification_method"] = event.value
        self._update_section("notifications", notifications)
        self._apply_notifications_state(event.value)

    @on(Input.Changed, "#notifications-snippet")
    def _on_notifications_snippet(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        self._update_int_field("notifications", "snippet_chars", event.value, "notifications-error")

    @on(Input.Changed, "#notifications-bot")
    def _on_notifications_bot(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        notifications = self._get_section("notifications")
        value = event.value.strip()
        if value:
            notifications["bot_chat_id"] = value
        else:
            notifications.pop("bot_chat_id", None)
        self._update_section("notifications", notifications)

    @on(Switch.Changed, "#catchup-enabled")
    def _on_catchup_enabled(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        catch_up = self._get_section("catch_up")
        catch_up["enabled"] = bool(event.value)
        self._update_section("catch_up", catch_up)

    @on(Input.Changed, "#catchup-messages")
    def _on_catchup_messages(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        self._update_int_field("catch_up", "messages_per_source", event.value, "catchup-error")

    @on(Switch.Changed, "#logging-enabled")
    def _on_logging_enabled(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        logging["enabled"] = bool(event.value)
        self._update_section("logging", logging)

    @on(Select.Changed, "#logging-level")
    def _on_logging_level(self, event: Select.Changed) -> None:
        if self._loading_form or event.value is Select.BLANK:
            return
        logging = self._get_section("logging")
        logging["level"] = event.value
        self._update_section("logging", logging)

    @on(Switch.Changed, "#logging-console")
    def _on_logging_console(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        logging["console"] = bool(event.value)
        self._update_section("logging", logging)

    @on(Switch.Changed, "#logging-file-enabled")
    def _on_logging_file_enabled(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        file_cfg = self._get_subdict(logging, "file")
        file_cfg["enabled"] = bool(event.value)
        logging["file"] = file_cfg
        self._update_section("logging", logging)
        redact_enabled = bool(self._get_subdict(logging, "redact").get("enabled", False))
        self._apply_logging_state(bool(event.value), redact_enabled)

    @on(Input.Changed, "#logging-file-path")
    def _on_logging_file_path(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        file_cfg = self._get_subdict(logging, "file")
        file_cfg["path"] = event.value
        logging["file"] = file_cfg
        self._update_section("logging", logging)

    @on(Input.Changed, "#logging-file-max-bytes")
    def _on_logging_file_max(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        self._update_nested_int_field(
            "logging",
            ("file", "max_bytes"),
            event.value,
            "logging-error",
        )

    @on(Input.Changed, "#logging-file-backup")
    def _on_logging_file_backup(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        self._update_nested_int_field(
            "logging",
            ("file", "backup_count"),
            event.value,
            "logging-error",
        )

    @on(Switch.Changed, "#logging-redact-enabled")
    def _on_logging_redact_enabled(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        redact_cfg = self._get_subdict(logging, "redact")
        redact_cfg["enabled"] = bool(event.value)
        logging["redact"] = redact_cfg
        self._update_section("logging", logging)
        file_enabled = bool(self._get_subdict(logging, "file").get("enabled", False))
        self._apply_logging_state(file_enabled, bool(event.value))

    @on(TextArea.Changed, "#logging-redact-patterns")
    def _on_logging_redact_patterns(self, event: TextArea.Changed) -> None:
        if self._loading_form:
            return
        logging = self._get_section("logging")
        redact_cfg = self._get_subdict(logging, "redact")
        patterns = [line.strip() for line in event.text_area.text.splitlines() if line.strip()]
        redact_cfg["patterns"] = patterns
        logging["redact"] = redact_cfg
        self._update_section("logging", logging)

    def _update_int_field(self, section: str, key: str, value: str, error_id: str) -> None:
        parsed = self._parse_int(value, error_id)
        if parsed is None:
            return
        config = self._get_section(section)
        config[key] = parsed
        self._update_section(section, config)

    def _update_nested_int_field(
        self,
        section: str,
        path: tuple[str, str],
        value: str,
        error_id: str,
    ) -> None:
        parsed = self._parse_int(value, error_id)
        if parsed is None:
            return
        config = self._get_section(section)
        nested = self._get_subdict(config, path[0])
        nested[path[1]] = parsed
        config[path[0]] = nested
        self._update_section(section, config)

    def _parse_int(self, value: str, error_id: str) -> Optional[int]:
        stripped = value.strip()
        if not stripped:
            self._set_error(error_id, "")
            return None
        if not stripped.isdigit():
            self._set_error(error_id, "Enter a non-negative integer")
            return None
        self._set_error(error_id, "")
        return int(stripped)

    @staticmethod
    def _coerce_row_key(value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    @staticmethod
    def _get_subdict(parent: dict[str, Any], key: str) -> dict[str, Any]:
        value = parent.get(key)
        if isinstance(value, dict):
            return value
        return {}
