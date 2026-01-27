"""Application entry point for the telescope watcher."""

from __future__ import annotations
import random
import logging
import os

from art import tprint
from telethon import events
import settings
from adapters.sqlite_storage import SQLiteStorage
from adapters.telegram_mapper import build_context
from adapters.telegram_bot_notifier import TelegramBotNotifier
from adapters.telegram_notifier import TelegramSavedMessagesNotifier
from client import build_client
from core.config import DedupConfig
from core.processor import MessageProcessor
from core.rules_engine import build_rules
from get_session import authorize

NAME = "TELESCOPE"
FONT = "tarty-1"
def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _dialog_title(dialog) -> str:
    # Dialog names can be missing or partial depending on entity type. We pick
    # the best available label to keep the discovery output usable.
    if dialog.name:
        return dialog.name

    entity = dialog.entity
    first = getattr(entity, "first_name", "") or ""
    last = getattr(entity, "last_name", "") or ""
    full = f"{first} {last}".strip()
    if full:
        return full

    username = getattr(entity, "username", None)
    if username:
        return username

    return "Unknown"


def _dialog_type(dialog) -> str:
    # We keep a small set of types to match the user's mental model.
    if dialog.is_channel:
        if getattr(dialog.entity, "megagroup", False):
            return "supergroup"
        return "channel"
    if dialog.is_group:
        return "group"
    return "unknown"


def _source_key_from_dialog(dialog) -> str:
    # Use the same normalization rule as the core mapper: usernames use @,
    # otherwise fall back to chat_id:<id> for uniform handling.
    username = getattr(dialog.entity, "username", None)
    if username:
        return f"@{username.lower()}"
    return f"chat_id:{dialog.id}"


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


def _startup_menu(client) -> None:
    # The menu exists to make chat_id discovery accessible to non-technical
    # users. By default we only show username-less archived dialogs because
    # those are the ones that require chat_id references in config.json, and we
    # skip private chats to focus on group monitoring.
    try:
        while True:
            tprint(NAME, FONT, space=1)
            print("[1] List archived group chats without usernames (chat_id discovery)")
            print("[2] Start watcher")
            print("[3] Exit")
            print("\nSelect an option: ")
            choice = input("telescope> ").strip()

            if choice == "1":
                client.loop.run_until_complete(_list_archived_dialogs(client, True))
                input("Press Enter to return to the menu...")
            elif choice == "2":
                return
            elif choice == "3":
                raise SystemExit(0)
            else:
                print("Invalid option. Please choose 1, 2, or 3.")
    except KeyboardInterrupt:
        exit(0)


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
) -> None:
    """Run a startup catch-up scan before registering real-time handlers."""

    if not settings.CATCH_UP_ENABLED:
        return

    tracked_sources = storage.list_sources_state()
    sources_to_scan = settings.SOURCES.intersection(tracked_sources)

    if not sources_to_scan:
        return

    messages_checked = 0
    matches_found = 0

    for source_key in sources_to_scan:
        last_id = storage.get_last_id(source_key) or 0
        max_id_seen = last_id

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
            if message.id <= last_id:
                continue
            messages_checked += 1
            max_id_seen = max(max_id_seen, message.id)
            context = build_context(message)
            await processor.handle(context)

        # Always update to the newest message id we touched to avoid repeats.
        storage.set_last_id(source_key, max_id_seen)

    matches_found = counting_notifier.matches_sent

    logging.getLogger(__name__).info(
        "Catch-up scan complete: sources=%s, messages=%s, matches=%s",
        len(sources_to_scan),
        messages_checked,
        matches_found,
    )


def main() -> None:
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
    logger.info('%s rules are loaded', len(rules))

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
    client.loop.run_until_complete(_catch_up_scan(
        client,
        storage,
        catch_up_processor,
        catch_up_notifier,
    ))

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
            context = build_context(event.message)
            await processor.handle(context)
        except Exception:
            logger.exception("Error while processing message")

    # Explicit lifecycle management makes start/shutdown behavior obvious.
    client.start()
    _startup_menu(client)
    logger.info("Client connected. Listening for incoming messages...")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()

#TODO добавить тесты pytest
#TODO ?сделать отдельную опцию в меню catchup вместо автоматического включения. В конфиге больше такой опции включения не будет, кроме количества сообщений.
#TODO добавить возможность логирования в файл
#TODO прикрутить нейронку для создания правил


