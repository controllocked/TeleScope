"""Textual-based config panel skeleton for Telescope."""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Center, Container, Horizontal, Vertical
from textual.widgets import Static, Tab, Tabs


TELEGRAM_BLUE = "#2AABEE"


class ConfigPanelApp(App):
    """Skeleton TUI with tabs for the Telescope config panel."""

    CSS = """
    Screen {
        background: #0f1a21;
        color: #e8eef5;
    }

    #header {
        height: 8;
        padding: 1 4;
        border-bottom: solid #2a3a46;
    }

    #header-row {
        height: 6;
    }

    #header-left, #header-right {
        width: 1fr;
    }

    #header-right {
        content-align: right top;
        text-align: right;
    }

    #title {
        text-style: bold;
    }

    .subtle {
        color: #c6d2dd;
    }

    #tabs-bar {
        height: 5;
        padding: 0 4;
        border-bottom: solid #2a3a46;
        align: center middle;
    }

    #tabs-center {
        width: 100%;
        height: 4;
        align: center middle;
    }

    #tabs {
        width: auto;
        min-width: 0;
        padding: 0;
    }

    Tab {
        height: 3;
        text-style: bold;
    }

    #tabs > #tabs-scroll {
        width: auto;
    }

    #tabs #tabs-list-bar, #tabs #tabs-list {
        width: auto;
        min-width: 0;
    }

    #tabs #tabs-list {
        align: center middle;
    }

    #tabs Underline {
        width: auto;
    }

    #tab-content {
        height: 1fr;
        content-align: center middle;
        color: #c6d2dd;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="header"):
            with Horizontal(id="header-row"):
                with Vertical(id="header-left"):
                    yield Static(self._title_text(), id="title")
                    yield Static("engine v1.0.0", classes="subtle")
                with Vertical(id="header-right"):
                    yield Static("session: active", classes="subtle")
                    yield Static("db: telescope.db", classes="subtle")

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

        yield Static("", id="tab-content")

    def on_mount(self) -> None:
        self._set_content_from_label("Sources")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        label = event.tab.label
        if hasattr(label, "plain"):
            label = label.plain
        self._set_content_from_label(str(label))

    def _set_content_from_label(self, label: str) -> None:
        content = self.query_one("#tab-content", Static)
        content.update(Text(f"*{label}*"))

    @staticmethod
    def _title_text() -> Text:
        return Text.assemble(
            ("TELE", TELEGRAM_BLUE),
            ("SCOPE > Config Panel", "bold"),
        )


if __name__ == "__main__":
    ConfigPanelApp().run()
