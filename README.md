# telescope

A clean, minimal Telegram watcher that listens to new incoming messages from a
hardcoded list of sources, applies simple content rules, stores matches in
SQLite, and notifies your Saved Messages ("me"). This is a **user-session**
watcher built on Telethon, not a bot.

## What it does
- Monitors incoming messages for the configured sources
- Applies keyword/regex rules with optional excludes
- Stores match metadata in SQLite for traceability
- Notifies your Saved Messages with a compact snippet
- Avoids repeats via message-level idempotency and optional deduplication

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure
1) Copy the example env file:
```bash
cp .env.example .env
```
2) Fill in `API_ID` and `API_HASH` from https://my.telegram.org.

3) Edit sources and rules in `src/settings.py`:
- `SOURCES` is a set of normalized keys:
  - public usernames: `"@channel_or_group"` (lowercase)
  - any chat by id: `"chat_id:<event.chat_id>"`
- `RULES` are dicts with `name`, `keywords`, optional `regex`, optional `exclude_keywords`.

## Run
```bash
python src/app.py
```

At startup you'll see a simple menu. The default option lists **archived**
group chats without usernames to help you discover `chat_id` values to paste
into `SOURCES` in `src/settings.py`. Telescope never auto-adds chats.

## Debug tip
If filtering by source fails, temporarily log `event.chat_id` and
`event.chat.username` inside the handler in `src/app.py` to
discover the correct identifier to add to `SOURCES`.

## Limitations
- Only new messages after start are seen; history is not backfilled.
- You must have access to the monitored chats for messages to be delivered.
- Permalinks may be `None` for private chats or chats without usernames.

## Next steps (beyond MVP)
- Implement alert system
- Config file or DB-backed rules for easier updates without code changes.
- A lightweight scheduler for periodic dedup cleanup.
- Richer rule logic (per-rule severity, AND/OR groups, or phrase proximity).
- Message exporting or web UI for browsing match history.
