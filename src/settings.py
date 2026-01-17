"""Static configuration for telescope.

All sources and rules are hardcoded here to keep the MVP simple, transparent,
and safe to restart. The design choice trades flexibility (no hot reloading or
DB-backed config) for clarity and predictability.
"""

import os

# Where to store the SQLite database.
# Keeping it next to the code makes the MVP self-contained and easy to locate.
DB_PATH = os.path.join(os.path.dirname(__file__), "telescope.db")

# Sources to monitor. Keys are normalized and MUST follow this rule:
# - If a chat has a username, use "@<username>" in lowercase
# - Otherwise use "chat_id:<event.chat_id>"
# This lets us uniformly handle channels, groups, supergroups, and private chats.
SOURCES = {
    "@testiktestik111",  # public channel/group by username
    "chat_id:1816083518",  # private chat or any chat without a username
}

# Rules define what counts as a match. Each rule can include:
# - name: human-readable label for logging and notifications
# - keywords: list of case-insensitive substrings (any match triggers)
# - regex: optional list of regex patterns (any match triggers)
# - exclude_keywords: optional list of case-insensitive substrings to negate
RULES = [
    {
        "name": "Sosal detect",
        "keywords": ["sosal", "сосал"],
        "regex": [],
        "exclude_keywords": []
    }
    ,{
        "name": "Hiring",
        "keywords": ["hiring", "we are hiring", "looking for"],
        "regex": [r"\b(opening|role|position)\b"],
        "exclude_keywords": ["not hiring", "no hiring"],
    },
    {
        "name": "Funding",
        "keywords": ["seed round", "series a", "series b"],
        "regex": [r"\braised\s+\$?\d+"],
        "exclude_keywords": [],
    },
    {
        'name':'Manchester City',
        'keywords':['Haaland','mc','england'],
        'regex': [],
        'exclude_keywords': ['проиграл', 'lose']
    }
]

# Deduplication controls to reduce notification spam for repeated content.
# - DEDUP_MODE: "off", "per_source", or "global"
# - DEDUP_ONLY_ON_MATCH: only store fingerprints when a rule matched
# - DEDUP_TTL_DAYS: cleanup horizon for fingerprints
DEDUP_MODE = "per_source"
DEDUP_ONLY_ON_MATCH = True
DEDUP_TTL_DAYS = 30

# Notification snippet size for Saved Messages.
SNIPPET_CHARS = 400
