"""Main Textual app for the Telescope config panel."""

from __future__ import annotations

import json
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Center, Container, Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Footer, Static, Tab, Tabs

from .constants import CONFIG_PATH, TELEGRAM_BLUE
from .modals import ReloadConfirmScreen, UnsavedChangesScreen
from .tabs.account import AccountTab
from .tabs.data import DataTab
from .tabs.guide import GuideTab
from .tabs.rules import RulesTab
from .tabs.settings import SettingsTab
from .tabs.sources import SourcesTab
from .state import ConfigState


class ConfigPanelApp(App):
    """Config panel with global config state and tabs."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config_state = ConfigState()

    BINDINGS = [
        ("ctrl+s", "save_config", "Save"),
        ("ctrl+r", "reload_config", "Reload"),
        ("q", "request_quit", "Quit"),
        ("ctrl+c", "request_quit", "Quit"),
    ]

    CSS_PATH = "app.tcss"


    def compose(self) -> ComposeResult:
        with Container(id="header"):
            with Horizontal(id="header-row"):
                with Vertical(id="header-left"):
                    yield Static(self._title_text(), id="title")
                    yield Static("engine v1.0.0", classes="subtle")
                with Vertical(id="header-right"):
                    yield Static("session: active", classes="subtle")
                    yield Static("db: telescope.db", classes="subtle")
                    yield Static("", id="header-status")
                    yield Horizontal(
                        Button("Save", id="save-btn"),
                        Button("Reload", id="reload-btn"),
                        id="header-actions",
                    )

        with Container(id="tabs-bar"):
            with Center(id="tabs-center"):
                yield Tabs(
                    Tab("Sources", id="sources"),
                    Tab("Rules", id="rules"),
                    Tab("Settings", id="settings"),
                    Tab("Account", id="account"),
                    Tab("Data", id="data"),
                    Tab("Guide", id="guide"),
                    id="tabs",
                )

        with ContentSwitcher(id="content"):
            yield SourcesTab(id="sources")
            yield RulesTab(id="rules")
            yield SettingsTab(id="settings")
            yield AccountTab(id="account")
            yield DataTab(id="data")
            yield GuideTab(id="guide")
        yield Footer()

    def on_mount(self) -> None:
        self._load_config()
        self._set_active_tab("sources")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        tab_id = event.tab.id or ""
        if not tab_id:
            label = event.tab.label
            if hasattr(label, "plain"):
                label = label.plain
            tab_id = str(label).strip().lower()
        self._set_active_tab(tab_id)

    def _set_active_tab(self, tab_id: str) -> None:
        switcher = self.query_one("#content", ContentSwitcher)
        switcher.current = tab_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.action_save_config()
        elif event.button.id == "reload-btn":
            self.action_reload_config()

    def action_save_config(self) -> None:
        self._save_config()

    def action_reload_config(self) -> None:
        if self.config_state.dirty:
            self.push_screen(ReloadConfirmScreen(), self._handle_reload_choice)
        else:
            self._load_config()

    def action_request_quit(self) -> None:
        if self.config_state.dirty:
            self.push_screen(UnsavedChangesScreen(), self._handle_exit_choice)
        else:
            self.exit()

    def _handle_exit_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self._save_config():
                self.exit()
        elif choice == "discard":
            self.exit()
        else:
            return

    def _handle_reload_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self._save_config():
                self._load_config()
        elif choice == "reload":
            self._load_config()
        else:
            return

    def _load_config(self) -> None:
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("config root must be an object")
            self.config_state.data = loaded
            self.config_state.dirty = False
            self.config_state.error = None
        except FileNotFoundError:
            self.config_state.data = None
            self.config_state.dirty = False
            self.config_state.error = "config.json missing"
        except json.JSONDecodeError as exc:
            self.config_state.data = None
            self.config_state.dirty = False
            self.config_state.error = f"config.json error: {exc.msg}"
        except ValueError as exc:
            self.config_state.data = None
            self.config_state.dirty = False
            self.config_state.error = str(exc)
        self._refresh_header()
        self._refresh_sources_tab()

    def _save_config(self) -> bool:
        if self.config_state.data is None:
            self.config_state.error = "Nothing to save"
            self._refresh_header()
            return False
        try:
            CONFIG_PATH.write_text(
                json.dumps(self.config_state.data, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            self.config_state.dirty = False
            self.config_state.error = None
            self._refresh_header()
            return True
        except OSError as exc:
            self.config_state.error = f"save failed: {exc.strerror or exc}"
            self._refresh_header()
            return False

    def mark_dirty(self) -> None:
        self.config_state.dirty = True
        self._refresh_header()

    def _refresh_header(self) -> None:
        status = self.query_one("#header-status", Static)
        save_btn = self.query_one("#save-btn", Button)
        reload_btn = self.query_one("#reload-btn", Button)

        status.remove_class("status-loaded", "status-modified", "status-error")
        if self.config_state.error:
            status.update("config: error")
            status.add_class("status-error")
        elif self.config_state.dirty:
            status.update("config: modified *")
            status.add_class("status-modified")
        else:
            status.update("config: loaded")
            status.add_class("status-loaded")

        save_btn.disabled = self.config_state.data is None or not self.config_state.dirty
        reload_btn.disabled = False

    def _refresh_sources_tab(self) -> None:
        try:
            sources_tab = self.query_one(SourcesTab)
        except Exception:
            return
        sources_tab.reload_from_config()

    def update_config_section(self, section: str, value: Any) -> None:
        """Update a config section in memory and mark dirty."""
        if self.config_state.data is None:
            self.config_state.data = {}
        self.config_state.data[section] = value
        self.mark_dirty()

    @staticmethod
    def _title_text() -> Text:
        return Text.assemble(
            ("TELE", TELEGRAM_BLUE),
            ("SCOPE > Config Panel", "bold"),
        )

