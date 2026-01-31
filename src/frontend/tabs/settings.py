"""Settings tab placeholder."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Static


class SettingsTab(Container):
    def compose(self):
        yield Static("*Settings*", classes="placeholder")
