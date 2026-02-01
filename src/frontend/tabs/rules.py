"""Rules tab implementation."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, Switch, TextArea

from core.rules_engine import build_rules, match_rules
from ..modals import DeleteRuleScreen


class RulesTab(Container):
    """Rules tab for editing config.rules and testing rules."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loading_form = False
        self._current_row_key: Optional[str] = None
        self._table_ready = False

    def compose(self):
        with Vertical(id="rules-panel"):
            with Horizontal(id="rules-body"):
                with Container(id="rules-left"):
                    yield DataTable(id="rules-table", cursor_type="row")
                with Container(id="rules-right"):
                    yield Static("Rule editor", id="rules-title")
                    yield Static("name", classes="form-label")
                    yield Input(placeholder="Rule name", id="rule-name")
                    yield Static("enabled", classes="form-label")
                    yield Switch(value=True, id="rule-enabled")
                    with Horizontal(id="rules-keyword-row"):
                        with Container(id="rules-keywords-block"):
                            yield Static("keywords (one per line)", classes="form-label")
                            yield TextArea(id="rule-keywords")
                        with Container(id="rules-excludes-block"):
                            yield Static("exclude keywords (one per line)", classes="form-label")
                            yield TextArea(id="rule-excludes")
                    yield Static("regex (one pattern per line)", classes="form-label")
                    yield TextArea(id="rule-regex")
                    yield Static("Rule tester", id="rules-test-title")
                    yield TextArea(id="rule-test-text", placeholder="Paste text to test against rules")
                    with Horizontal(id="rules-test-actions"):
                        yield Button("Test", id="rule-test", variant="primary")
                    yield Static("", id="rule-test-result")
            with Horizontal(id="rules-actions"):
                yield Button("Add rule", id="add-rule", variant="success")
                yield Button("Duplicate rule", id="duplicate-rule")
                yield Button("Delete rule", id="delete-rule", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.add_column("enabled", key="enabled", width=8)
        table.add_column("name", key="name", width=38)
        table.add_column("badges", key="badges", width=26)
        table.zebra_stripes = True
        self.query_one("#rules-test-actions").styles.height = 3
        self._table_ready = True
        self.reload_from_config()
        self._set_form_state(None)

    def reload_from_config(self) -> None:
        if not self._table_ready:
            return
        table = self.query_one("#rules-table", DataTable)
        table.clear()
        for index, rule, badges in self._iter_rules():
            row_key = str(index)
            enabled_label = "yes" if rule.get("enabled", True) else "no"
            name = rule.get("name", "")
            table.add_row(enabled_label, name, badges, key=row_key)
        self._update_action_state()

    def _iter_rules(self) -> Iterable[tuple[int, dict[str, Any], str]]:
        for index, rule in enumerate(self._get_rules()):
            badges = self._badge_for_rule(rule)
            yield index, rule, badges

    def _badge_for_rule(self, rule: dict[str, Any]) -> str:
        keywords = rule.get("keywords", []) or []
        regexes = rule.get("regex", []) or []
        return f"keywords: {len(keywords)} regexes: {len(regexes)}"

    def _get_rules(self) -> list[dict[str, Any]]:
        data = self.app.config_state.data or {}
        rules = data.get("rules")
        if isinstance(rules, list):
            return rules
        return []

    def _set_rules(self, rules: list[dict[str, Any]]) -> None:
        self.app.update_config_section("rules", rules)

    def _update_action_state(self) -> None:
        delete_btn = self.query_one("#delete-rule", Button)
        duplicate_btn = self.query_one("#duplicate-rule", Button)
        has_selection = self._current_row_key is not None
        delete_btn.disabled = not has_selection
        duplicate_btn.disabled = not has_selection

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._current_row_key = self._coerce_row_key(event.row_key)
        self._set_form_state(self._current_row_key)
        self._update_action_state()

    @on(Input.Changed, "#rule-name")
    def _on_name_changed(self, event: Input.Changed) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        rules[index]["name"] = event.value
        self._set_rules(rules)
        self._update_table_cell(index, "name", event.value)

    @on(Switch.Changed, "#rule-enabled")
    def _on_enabled_changed(self, event: Switch.Changed) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        rules[index]["enabled"] = bool(event.value)
        self._set_rules(rules)
        self._update_table_cell(index, "enabled", "yes" if event.value else "no")

    @on(TextArea.Changed, "#rule-keywords")
    def _on_keywords_changed(self, event: TextArea.Changed) -> None:
        if self._loading_form:
            return
        self._update_lines_field(event.text_area.text, "keywords")

    @on(TextArea.Changed, "#rule-excludes")
    def _on_excludes_changed(self, event: TextArea.Changed) -> None:
        if self._loading_form:
            return
        self._update_lines_field(event.text_area.text, "exclude_keywords")

    @on(TextArea.Changed, "#rule-regex")
    def _on_regex_changed(self, event: TextArea.Changed) -> None:
        if self._loading_form:
            return
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        raw_lines = [line.strip() for line in event.text_area.text.splitlines()]
        regex_list = [line for line in raw_lines if line]
        rules[index]["regex"] = regex_list
        self._set_rules(rules)
        self._update_table_cell(index, "badges", self._badge_for_rule(rules[index]))

    def _update_lines_field(self, value: str, field: str) -> None:
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        parsed = [line.strip() for line in value.splitlines() if line.strip()]
        rules[index][field] = parsed
        self._set_rules(rules)
        self._update_table_cell(index, "badges", self._badge_for_rule(rules[index]))

    @on(Button.Pressed, "#add-rule")
    def _on_add_rule(self) -> None:
        rules = self._get_rules()
        rules.append(self._new_rule())
        self._set_rules(rules)
        self.reload_from_config()
        self._select_row(len(rules) - 1)

    @on(Button.Pressed, "#duplicate-rule")
    def _on_duplicate_rule(self) -> None:
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        rule = dict(rules[index])
        name = rule.get("name", "Rule") or "Rule"
        rule["name"] = f"{name} (copy)"
        rules.append(rule)
        self._set_rules(rules)
        self.reload_from_config()
        self._select_row(len(rules) - 1)

    @on(Button.Pressed, "#delete-rule")
    def _on_delete_rule(self) -> None:
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        name = rules[index].get("name", "")
        self.app.push_screen(DeleteRuleScreen(name), self._handle_delete_rule)

    def _handle_delete_rule(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        index = self._current_index()
        if index is None:
            return
        rules = self._get_rules()
        if index >= len(rules):
            return
        rules.pop(index)
        self._set_rules(rules)
        self._current_row_key = None
        self.reload_from_config()
        self._set_form_state(None)

    @on(Button.Pressed, "#rule-test")
    def _on_test_rule(self) -> None:
        test_text = self.query_one("#rule-test-text", TextArea).text
        result = self.query_one("#rule-test-result", Static)
        rules = self._get_rules()
        if not test_text.strip():
            result.update("Add test text to run.")
            return
        if not rules:
            result.update("No rules configured.")
            return
        enabled_override = []
        for rule in rules:
            clone = dict(rule)
            clone.setdefault("name", "(unnamed rule)")
            clone["enabled"] = True
            enabled_override.append(clone)
        compiled = build_rules(enabled_override)
        matches = match_rules(test_text, compiled)
        if not matches:
            result.update("Not matched")
            return
        lines = [f"Matched {len(matches)} rule(s):"]
        for match in matches:
            reason = match.reason.replace("\n", "; ")
            lines.append(f"- {match.rule_name}: {reason}")
        result.update("\n".join(lines))

    def _set_form_state(self, row_key: Optional[str]) -> None:
        self._loading_form = True
        name_input = self.query_one("#rule-name", Input)
        enabled_toggle = self.query_one("#rule-enabled", Switch)
        keywords_input = self.query_one("#rule-keywords", TextArea)
        excludes_input = self.query_one("#rule-excludes", TextArea)
        regex_input = self.query_one("#rule-regex", TextArea)
        if row_key is None:
            name_input.value = ""
            name_input.disabled = True
            enabled_toggle.value = False
            enabled_toggle.disabled = True
            keywords_input.text = ""
            keywords_input.disabled = True
            excludes_input.text = ""
            excludes_input.disabled = True
            regex_input.text = ""
            regex_input.disabled = True
        else:
            index = int(row_key)
            rules = self._get_rules()
            if index >= len(rules):
                self._loading_form = False
                return
            rule = rules[index]
            name_input.value = rule.get("name", "")
            name_input.disabled = False
            enabled_toggle.value = bool(rule.get("enabled", True))
            enabled_toggle.disabled = False
            keywords_input.text = "\n".join(rule.get("keywords", []) or [])
            keywords_input.disabled = False
            excludes_input.text = "\n".join(rule.get("exclude_keywords", []) or [])
            excludes_input.disabled = False
            regex_input.text = "\n".join(rule.get("regex", []) or [])
            regex_input.disabled = False
        self._loading_form = False

    def _select_row(self, index: int) -> None:
        table = self.query_one("#rules-table", DataTable)
        row_key = str(index)
        try:
            table.cursor_row = row_key
        except Exception:
            return
        self._current_row_key = row_key
        self._set_form_state(row_key)
        self._update_action_state()

    def _update_table_cell(self, index: int, column_key: str, value: Any) -> None:
        table = self.query_one("#rules-table", DataTable)
        row_key = str(index)
        try:
            table.get_row(row_key)
        except Exception:
            self.reload_from_config()
            return
        table.update_cell(row_key, column_key, value)

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

    @staticmethod
    def _new_rule() -> dict[str, Any]:
        return {
            "name": "New rule",
            "keywords": [],
            "exclude_keywords": [],
            "regex": [],
            "enabled": True,
        }
