"""Telegram client factory for telescope.

We explicitly manage the client's lifecycle (start/run_until_disconnected)
so it is obvious when the session is created and when it ends. This avoids
implicit context-manager behavior for a long-running watcher.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telethon import TelegramClient


def build_client() -> TelegramClient:
    """Create a Telethon client from environment variables.

    We read API_ID/API_HASH via python-dotenv to keep secrets out of the repo.
    The session name defaults to "telescope" to create a local .session file.
    """

    load_dotenv()

    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    session_name = os.getenv("SESSION_NAME", "telescope")

    # Fail fast on missing credentials to avoid an ambiguous login prompt.
    if not api_id or not api_hash:
        raise RuntimeError("Missing API_ID or API_HASH in environment")

    logging.getLogger(__name__).info("Initializing Telegram client")

    return TelegramClient(session_name, int(api_id), api_hash)
