"""Static configuration for telescope.

All user-editable settings (sources, rules, dedup, notifications) live in a
single JSON file for quick edits without touching Python.
"""

import json
import os

from core.source_keys import expand_source_key_variants

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Where to store the SQLite database.
DB_PATH = os.path.join(os.path.dirname(__file__), "telescope.db")

# Sources and surface settings are loaded from config.json so users can
# enable/disable chats, set aliases, and tweak dedup without editing code.
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")

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
        expanded_keys = expand_source_key_variants(source_key)
        sources.update(expanded_keys)
        alias = entry.get("alias")
        if alias:
            # Preserve explicit aliases for the configured key.
            aliases[source_key] = alias
            # Mirror aliases onto equivalent chat_id forms to avoid mismatches.
            for key in expanded_keys:
                if key == source_key:
                    continue
                aliases.setdefault(key, alias)
    return sources, aliases


_CONFIG = _load_json_config()

# Expose the raw config for modules that need structured access.
CONFIG = _CONFIG

# Enabled sources are used for filtering in the core processor.
SOURCES, SOURCE_ALIASES = _normalize_sources(_CONFIG.get("sources", []))

# Deduplication controls to reduce notification spam for repeated content.
# - DEDUP_MODE: "off", "per_source", or "global"
# - DEDUP_ONLY_ON_MATCH: only store fingerprints when a rule matched
# - DEDUP_TTL_DAYS: cleanup horizon for fingerprints
_dedup = _CONFIG.get("dedup", {})
DEDUP_MODE = _dedup.get("mode", "per_source")
DEDUP_ONLY_ON_MATCH = _dedup.get("only_on_match", True)
DEDUP_TTL_DAYS = int(_dedup.get("ttl_days", 30))

# Notification snippet size used by all notifier adapters.
_notifications = _CONFIG.get("notifications", {})
SNIPPET_CHARS = int(_notifications.get("snippet_chars", 400))
# Notification method switches adapters without changing core logic.
NOTIFICATION_METHOD = _notifications.get("notification_method", "saved_messages")
# Bot chat id is only required when notification_method=bot.
BOT_CHAT_ID = _notifications.get("bot_chat_id")

# Catch-up scan settings for startup backfill.
_catch_up = _CONFIG.get("catch_up", {})
CATCH_UP_ENABLED = bool(_catch_up.get("enabled", False))
CATCH_UP_MESSAGES_PER_SOURCE = int(_catch_up.get("messages_per_source", 50))

# Rules are pulled directly from config.json, keeping them alongside sources.
RULES_CONFIG = _CONFIG.get("rules", [])

# Logging configuration (optional).
LOGGING = _CONFIG.get("logging", {})
