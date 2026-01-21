"""Static configuration for telescope.

Sources and lightweight settings are loaded from JSON for quick edits without
touching Python, while rules live in their own JSON file.

Not recommended to edit dedup settings
"""

import json
import os

# Where to store the SQLite database.
DB_PATH = os.path.join(os.path.dirname(__file__), "telescope.db")

# Sources and surface settings are loaded from config.json so users can
# enable/disable chats, set aliases, and tweak dedup without editing code.
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))

# Rules are loaded from config.json to keep all settings in one place.
def _load_json_config() -> dict:
    """Load config.json with a flat, user-friendly schema."""

    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_sources(raw_sources: list[dict]) -> tuple[set[str], dict[str, str]]:
    """Normalize sources and build an alias map keyed by source_key."""

    sources: set[str] = set()
    aliases: dict[str, str] = {}
    for entry in raw_sources:
        source_key = entry.get("source_key")
        if not source_key:
            continue
        if not entry.get("enabled", True):
            continue
        sources.add(source_key)
        alias = entry.get("alias")
        if alias:
            aliases[source_key] = alias
    return sources, aliases


_CONFIG = _load_json_config()

# Expose the raw config for modules that need structured access.
CONFIG = _CONFIG

# Enabled sources are used for filtering in the pipeline.
SOURCES, SOURCE_ALIASES = _normalize_sources(_CONFIG.get("sources", []))

# Deduplication controls to reduce notification spam for repeated content.
# - DEDUP_MODE: "off", "per_source", or "global"
# - DEDUP_ONLY_ON_MATCH: only store fingerprints when a rule matched
# - DEDUP_TTL_DAYS: cleanup horizon for fingerprints
_dedup = _CONFIG.get("dedup", {})
DEDUP_MODE = _dedup.get("mode", "per_source")
DEDUP_ONLY_ON_MATCH = _dedup.get("only_on_match", True)
DEDUP_TTL_DAYS = int(_dedup.get("ttl_days", 30))

# Notification snippet size for Saved Messages.
_notifications = _CONFIG.get("notifications", {})
SNIPPET_CHARS = int(_notifications.get("snippet_chars", 400))

# Rules are pulled directly from config.json, keeping them alongside sources.
RULES_CONFIG = _CONFIG.get("rules", [])
