"""Account tab placeholder."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Static


class AccountTab(Container):
    def compose(self):
        yield Static("*Account*", classes="placeholder")
