from __future__ import annotations

from core.rules_engine import build_rules, match_rules


def test_build_rules_defaults_tags_to_empty_list() -> None:
    rules = build_rules([{"name": "r1", "keywords": ["foo"], "enabled": True}])
    assert len(rules) == 1
    assert rules[0].tags == []


def test_build_rules_parses_tags() -> None:
    rules = build_rules(
        [
            {
                "name": "r1",
                "keywords": ["foo"],
                "tags": ["severity:critical", "category:cve"],
                "enabled": True,
            }
        ]
    )
    assert rules[0].tags == ["severity:critical", "category:cve"]


def test_build_rules_strips_and_drops_empty_tags() -> None:
    rules = build_rules(
        [
            {
                "name": "r1",
                "keywords": ["foo"],
                "tags": ["  severity:high  ", "", "   ", "actor:lockbit"],
                "enabled": True,
            }
        ]
    )
    assert rules[0].tags == ["severity:high", "actor:lockbit"]


def test_match_rules_propagates_tags() -> None:
    rules = build_rules(
        [
            {
                "name": "r1",
                "keywords": ["foo"],
                "tags": ["severity:high"],
                "enabled": True,
            }
        ]
    )
    matches = match_rules("hello foo bar", rules)
    assert len(matches) == 1
    assert matches[0].tags == ["severity:high"]


def test_match_rules_without_tags() -> None:
    rules = build_rules([{"name": "r1", "keywords": ["foo"], "enabled": True}])
    matches = match_rules("foo here", rules)
    assert matches[0].tags == []
