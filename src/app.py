"""Application entry point for the telescope watcher."""

from __future__ import annotations

import argparse
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

from art import tprint
from dotenv import load_dotenv
from telethon import events
import settings
from adapters.sqlite_storage import SQLiteStorage
from adapters.telegram_mapper import ForumResolver, build_context
from adapters.telegram_bot_notifier import TelegramBotNotifier
from adapters.telegram_notifier import TelegramSavedMessagesNotifier
from client import build_client
from core.config import DedupConfig
from core.processor import MessageProcessor
from core.rules_engine import build_rules
from core.source_keys import split_source_key
from get_session import authorize

NAME = "TELESCOPE"
FONT = "tarty-1"


def _print_banner() -> None:
    tprint(NAME, FONT, space=1)
class _RedactingFormatter(logging.Formatter):
    def __init__(self, secrets: list[str], fmt: str, datefmt: Optional[str] = None) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._secrets = [secret for secret in secrets if secret]

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for secret in self._secrets:
            message = message.replace(secret, "***")
        return message


def _collect_redaction_values(config: dict) -> list[str]:
    redact_cfg = config.get("redact", {}) if config else {}
    if not redact_cfg.get("enabled", False):
        return []
    values = []
    for name in redact_cfg.get("patterns", []):
        value = os.getenv(name)
        if value:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def _configure_logging() -> None:
    config = settings.LOGGING or {}
    if not config.get("enabled", False):
        return

    load_dotenv()
    level_name = str(config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    secrets = _collect_redaction_values(config)
    formatter = _RedactingFormatter(secrets, fmt=fmt, datefmt=datefmt)

    handlers: list[logging.Handler] = []

    if config.get("console", True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    file_cfg = config.get("file", {})
    if file_cfg.get("enabled", False):
        path = file_cfg.get("path", "logs/telescope.log")
        if not os.path.isabs(path):
            path = os.path.join(settings.PROJECT_ROOT, path)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        max_bytes = int(file_cfg.get("max_bytes", 5 * 1024 * 1024))
        backup_count = int(file_cfg.get("backup_count", 5))
        file_handler = RotatingFileHandler(
            path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    if not handlers:
        return

    logging.basicConfig(level=level, handlers=handlers)


class _CountingNotifier:
    """Wrap a notifier to count matches during the catch-up scan."""

    def __init__(self, wrapped) -> None:
        self._wrapped = wrapped
        self.matches_sent = 0

    async def send(self, context, match, snippet) -> None:
        self.matches_sent += 1
        await self._wrapped.send(context, match, snippet)


async def _catch_up_scan(
    client,
    storage: SQLiteStorage,
    processor: MessageProcessor,
    counting_notifier: _CountingNotifier,
    forum_resolver: ForumResolver,
) -> None:
    """Run a startup catch-up scan before registering real-time handlers."""

    if not settings.CATCH_UP_ENABLED:
        return

    tracked_sources = storage.list_sources_state()
    tracked_bases = {split_source_key(key)[0] for key in tracked_sources}
    sources_to_scan: set[str] = set()
    for source_key in settings.SOURCES:
        base_key, _ = split_source_key(source_key)
        if base_key in tracked_bases:
            sources_to_scan.add(base_key)

    if not sources_to_scan:
        return

    messages_checked = 0
    matches_found = 0

    for source_key in sources_to_scan:
        max_id_seen = 0
        try:
            if source_key.startswith("@"):
                entity = await client.get_entity(source_key)
            else:
                chat_id = int(source_key.split("chat_id:", 1)[1])
                entity = await client.get_entity(chat_id)
        except Exception:
            logging.getLogger(__name__).exception("Failed to resolve source %s during catchup", source_key)
            continue

        messages = []
        async for message in client.iter_messages(entity, limit=settings.CATCH_UP_MESSAGES_PER_SOURCE):
            messages.append(message)

        for message in reversed(messages):
            messages_checked += 1
            max_id_seen = max(max_id_seen, message.id)
            context = await build_context(message, forum_resolver)
            await processor.handle(context)

        # Always update to the newest message id we touched to avoid repeats.
        # We keep a base-key marker to unblock catch-up on future restarts.
        if max_id_seen:
            storage.set_last_id(source_key, max_id_seen)

    matches_found = counting_notifier.matches_sent

    logging.getLogger(__name__).info(
        "Catch-up scan complete: sources=%s, messages=%s, matches=%s",
        len(sources_to_scan),
        messages_checked,
        matches_found,
    )


def _run() -> None:
    _print_banner()
    _configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting telescope")

    storage = SQLiteStorage(settings.DB_PATH)
    storage.init_db()
    if settings.DEDUP_MODE != "off":
        removed = storage.cleanup_seen(settings.DEDUP_TTL_DAYS)
        logger.info("Dedup cleanup removed %s fingerprints", removed)

    # Load rules from config.json so edits are quick.
    rules = build_rules(settings.RULES_CONFIG)
    dedup_config = DedupConfig(
        mode=settings.DEDUP_MODE,
        only_on_match=settings.DEDUP_ONLY_ON_MATCH,
        ttl_days=settings.DEDUP_TTL_DAYS,
    )
    logger.info("%s rules are loaded", len(rules))

    client = build_client()
    client.loop.run_until_complete(client.connect())
    client.loop.run_until_complete(authorize(client))

    # Select the notification adapter based on configuration to keep the core
    # processor independent from delivery details.
    if settings.NOTIFICATION_METHOD == "bot":
        bot_token = os.getenv("BOT_API")
        if not bot_token:
            raise RuntimeError("BOT_API is required when notification_method=bot")
        if not settings.BOT_CHAT_ID:
            raise RuntimeError("notifications.bot_chat_id is required for bot notifications")
        notifier = TelegramBotNotifier(
            bot_token=bot_token,
            chat_id=str(settings.BOT_CHAT_ID),
            source_aliases=settings.SOURCE_ALIASES,
        )
    elif settings.NOTIFICATION_METHOD == "saved_messages":
        notifier = TelegramSavedMessagesNotifier(client, settings.SOURCE_ALIASES)
    else:
        raise RuntimeError("notification_method must be 'saved_messages' or 'bot'")
    logger.info("Selected notification method - %s", settings.NOTIFICATION_METHOD)

    processor = MessageProcessor(
        rules=rules,
        storage=storage,
        notifier=notifier,
        allowed_sources=settings.SOURCES,
        dedup_config=dedup_config,
        snippet_chars=settings.SNIPPET_CHARS,
    )

    # Run catch-up before wiring real-time handlers to avoid missing messages
    # during a long scan and to keep history processing explicit.
    catch_up_notifier = _CountingNotifier(notifier)
    catch_up_processor = MessageProcessor(
        rules=rules,
        storage=storage,
        notifier=catch_up_notifier,
        allowed_sources=settings.SOURCES,
        dedup_config=dedup_config,
        snippet_chars=settings.SNIPPET_CHARS,
    )
    forum_resolver = ForumResolver(client)
    client.loop.run_until_complete(
        _catch_up_scan(
            client,
            storage,
            catch_up_processor,
            catch_up_notifier,
            forum_resolver,
        )
    )

    # Single handler keeps Telethon integration minimal and defers all filtering
    # to our core processor for consistency and testability.
    @client.on(events.NewMessage(incoming=True))
    async def handler(event) -> None:
        try:
            # When using bot notifications, ignore bot-sent messages to avoid
            # loops or accidental processing of our own alerts.
            if settings.NOTIFICATION_METHOD == "bot":
                sender = await event.get_sender()
                if event.is_private and sender and getattr(sender, "bot", False):
                    return
            context = await build_context(event.message, forum_resolver)
            await processor.handle(context)
        except Exception:
            logger.exception("Error while processing message")

    # Explicit lifecycle management makes start/shutdown behavior obvious.
    client.start()
    logger.info("Client connected. Listening for incoming messages...")
    client.run_until_disconnected()


def _setup() -> None:
    _print_banner()
    from frontend.app import ConfigPanelApp

    ConfigPanelApp().run()


def _dialog_type(dialog: Any) -> str:
    if getattr(dialog, "is_channel", False):
        entity = getattr(dialog, "entity", None)
        if getattr(entity, "megagroup", False):
            return "group"
        return "channel"
    if getattr(dialog, "is_group", False):
        return "group"
    if getattr(dialog, "is_user", False):
        return "user"
    return "chat"


def _dialog_title(dialog: Any) -> str:
    entity = getattr(dialog, "entity", None)
    title = getattr(entity, "title", None)
    if title:
        return str(title)
    name = getattr(dialog, "name", None)
    if name:
        return str(name)
    first = getattr(entity, "first_name", None)
    last = getattr(entity, "last_name", None)
    if first or last:
        return " ".join(part for part in [first, last] if part)
    entity_id = getattr(entity, "id", None)
    return str(entity_id or "unknown")


def _source_key_from_dialog(dialog: Any) -> str:
    entity = getattr(dialog, "entity", None)
    username = getattr(entity, "username", None)
    if username:
        return f"@{str(username).lower()}"
    dialog_id = getattr(dialog, "id", None) or getattr(entity, "id", None)
    return f"chat_id:{dialog_id}"


async def _list_archived_dialogs(client, only_without_username: bool = True) -> None:
    # Archived dialogs are a user-curated list, making them ideal for discovery
    # without requiring commands, forwarding, or log inspection.
    dialogs = []
    async for dialog in client.iter_dialogs(archived=True, folder=1):
        username = getattr(dialog.entity, "username", None)
        # Username-less chats require chat_id:<id>, so we filter to them by
        # default to reduce noise and make copy-paste decisions obvious.
        if only_without_username and username:
            continue
        # Skip private 1:1 chats; the discovery menu focuses on group contexts.
        if dialog.is_user:
            continue
        dialogs.append(dialog)

    if not dialogs:
        print("No archived dialogs match the current filter.")
        return

    for index, dialog in enumerate(dialogs, start=1):
        dialog_type = _dialog_type(dialog)
        title = _dialog_title(dialog)
        source_key = _source_key_from_dialog(dialog)
        print(f"{index}. {dialog_type} | {title} | {source_key}")


def _discover() -> None:
    _print_banner()
    client = build_client()

    async def _run_discover() -> None:
        await client.connect()
        if not await client.is_user_authorized():
            print("Authorization required. Starting login...")
            await authorize(client)
        await _list_archived_dialogs(client)
        await client.disconnect()

    client.loop.run_until_complete(_run_discover())


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="telescope")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Start the watcher")
    subparsers.add_parser("config", help="Launch the config TUI")
    subparsers.add_parser(
        "discover",
        help="Shows private chats for discovery and scans them in the archive.",
    )

    args = parser.parse_args(argv)
    if args.command in {"setup", "config"}:
        _setup()
        return
    if args.command == "discover":
        _discover()
        return
    _run()


if __name__ == "__main__":
    main()
