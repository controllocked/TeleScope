"""Rule compilation and matching logic (core domain)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List


@dataclass(frozen=True)
class Rule:
    """Compiled rule used by the pipeline."""

    name: str
    keywords: List[str]
    exclude_keywords: List[str]
    regex_patterns: List[re.Pattern]
    raw_regex: List[str]


@dataclass(frozen=True)
class RuleMatch:
    """A single rule match with a human-readable reason."""

    rule_name: str
    reason: str


def build_rules(rules_config: Iterable[dict]) -> List[Rule]:
    """Normalize rule configs and compile regex patterns.

    This keeps per-message matching minimal and avoids any ambiguity about
    keyword casing or missing optional fields.
    """

    compiled: List[Rule] = []
    for rule in rules_config:
        if not rule.get("enabled", True):
            continue
        keywords = [k.lower() for k in rule.get("keywords", [])]
        exclude_keywords = [k.lower() for k in rule.get("exclude_keywords", [])]
        raw_regex = rule.get("regex", []) or []
        regex_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in raw_regex]
        compiled.append(
            Rule(
                name=rule["name"],
                keywords=keywords,
                exclude_keywords=exclude_keywords,
                regex_patterns=regex_patterns,
                raw_regex=raw_regex,
            )
        )
    return compiled


def match_rules(text: str, rules: Iterable[Rule]) -> List[RuleMatch]:
    """Return all rule matches for the given text.

    Matching logic:
    - If any exclude keyword is present, the rule does not match.
    - Otherwise, any keyword OR any regex match is sufficient.
    - Reasons include the specific keywords and/or regex patterns that matched.
    """

    lowered = text.lower()
    matches: List[RuleMatch] = []

    for rule in rules:
        if any(ex in lowered for ex in rule.exclude_keywords):
            continue

        keyword_hits = [k for k in rule.keywords if k in lowered]
        regex_hits = [pattern.pattern for pattern in rule.regex_patterns if pattern.search(text)]

        if not keyword_hits and not regex_hits:
            continue

        reason_parts: List[str] = []
        if keyword_hits:
            reason_parts.append(f"keyword(s): {', '.join(sorted(set(keyword_hits)))}")
        if regex_hits:
            reason_parts.append(f"regex: {', '.join(sorted(set(regex_hits)))}")

        reason = "\n".join(reason_parts)
        matches.append(RuleMatch(rule_name=rule.name, reason=reason))

    return matches
