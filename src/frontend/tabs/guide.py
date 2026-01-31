"""Guide tab placeholder."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Static


class GuideTab(Container):
    def compose(self):
        yield Static("*Guide*", classes="placeholder")
