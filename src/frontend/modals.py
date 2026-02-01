"""Modal dialogs for the Textual config panel."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static, Switch

from .validators import parse_source_key


class UnsavedChangesScreen(ModalScreen[str]):
    """Prompt when exiting with unsaved changes."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Unsaved changes", classes="modal-title"),
            Static("Save changes before exit?", classes="modal-body"),
            Horizontal(
                Button("Save", id="unsaved-save", variant="success"),
                Button("Discard", id="unsaved-discard", variant="error"),
                Button("Cancel", id="unsaved-cancel"),
                classes="modal-actions",
            ),
            classes="modal-dialog modal-dialog--confirm",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "unsaved-save":
            self.dismiss("save")
        elif event.button.id == "unsaved-discard":
            self.dismiss("discard")
        else:
            self.dismiss("cancel")


class ReloadConfirmScreen(ModalScreen[str]):
    """Prompt when reloading with unsaved changes."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Reload config?", classes="modal-title"),
            Static("Unsaved changes will be lost.", classes="modal-body"),
            Horizontal(
                Button("Save", id="reload-save"),
                Button("Reload", id="reload-reload", variant="warning"),
                Button("Cancel", id="reload-cancel"),
                classes="modal-actions",
            ),
            classes="modal-dialog modal-dialog--confirm",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reload-save":
            self.dismiss("save")
        elif event.button.id == "reload-reload":
            self.dismiss("reload")
        else:
            self.dismiss("cancel")


class AddSourceScreen(ModalScreen[dict[str, Any] | None]):
    """Modal form for adding a new source."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add source", classes="modal-title"),
            Static("", id="add-error", classes="modal-error"),
            Static("source_key", classes="form-label"),
            Input(placeholder="@channel or chat_id:123", id="add-source-key"),
            Static("alias (optional)", classes="form-label"),
            Input(placeholder="Alias", id="add-alias"),
            Static("enabled", classes="form-label"),
            Switch(value=True, id="add-enabled"),
            Horizontal(
                Button("Add", id="add-confirm", variant="success"),
                Button("Cancel", id="add-cancel"),
                classes="modal-actions",
            ),
            classes="modal-dialog modal-dialog--form",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-cancel":
            self.dismiss(None)
            return
        if event.button.id != "add-confirm":
            return
        source_key = self.query_one("#add-source-key", Input).value
        alias = self.query_one("#add-alias", Input).value.strip()
        enabled = self.query_one("#add-enabled", Switch).value
        info = parse_source_key(source_key)
        error = self.query_one("#add-error", Static)
        if info.error or info.normalized is None:
            error.update(info.error or "invalid source_key")
            return
        payload: dict[str, Any] = {"source_key": info.normalized, "enabled": bool(enabled)}
        if alias:
            payload["alias"] = alias
        self.dismiss(payload)


class DeleteSourceScreen(ModalScreen[bool]):
    """Confirm deletion of a source."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        self._source_key = source_key

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Delete source?", classes="modal-title"),
            Static(self._source_key, classes="modal-body"),
            Horizontal(
                Button("Delete", id="delete-confirm", variant="error"),
                Button("Cancel", id="delete-cancel"),
                classes="modal-actions",
            ),
            classes="modal-dialog modal-dialog--confirm",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)




class DeleteRuleScreen(ModalScreen[bool]):
    """Confirm deletion of a rule."""

    def __init__(self, rule_name: str) -> None:
        super().__init__()
        self._rule_name = rule_name or "(unnamed rule)"

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Delete rule?", classes="modal-title"),
            Static(self._rule_name, classes="modal-body"),
            Horizontal(
                Button("Delete", id="delete-rule-confirm", variant="error"),
                Button("Cancel", id="delete-rule-cancel"),
                classes="modal-actions",
            ),
            classes="modal-dialog modal-dialog--confirm",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-rule-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
