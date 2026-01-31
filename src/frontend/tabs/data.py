"""Data tab placeholder."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Static


class DataTab(Container):
    def compose(self):
        yield Static("*Data*", classes="placeholder")
