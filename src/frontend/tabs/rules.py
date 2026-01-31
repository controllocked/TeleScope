"""Rules tab placeholder."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Static


class RulesTab(Container):
    def compose(self):
        yield Static("*Rules*", classes="placeholder")
