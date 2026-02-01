 ![logo](logo.png)

A clean Telegram rule-based engine that listens to new incoming messages from a hardcoded list of sources, applies simple content rules, stores matches in SQLite, and notifies you. This is a user-session watcher built on Telethon, not a bot.
## What it does
- Monitors incoming messages for the configured sources
- Applies keyword/regex rules with optional excludes
- Stores match metadata in SQLite for traceability
- Notifies your Saved Messages with a compact snippet
- Avoids repeats via message-level idempotency and optional deduplication

## Who is this for

Telescope is intended for developers, analysts, and power users who want to monitor Telegram at scale using custom rules, without relying on bots or third-party services.

## Architecture (for growth)
The project is split into three explicit layers to keep the core logic reusable:
- `src/core`: domain logic (rules engine, dedup, message processing) with no Telegram or SQLite code.
- `src/adapters`: integration layers (Telegram mapping/notifications and SQLite storage).
- `src/app.py`: application layer (CLI menu, wiring, and lifecycle).
This separation keeps the core stable while letting you add new frontends or adapters later.

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Configure
1) Copy the example env file:
```bash
cp .env.example .env
```
2) Fill in `API_ID` and `API_HASH` from https://my.telegram.org.

3) Edit sources and rules in `config.json`:
- `config.json` uses a flat structure:
  - `sources`: list of objects with `source_key`, optional `alias`, and `enabled`
  - `rules`: list of objects with `name`, `keywords`, optional `regex`, optional `exclude_keywords`, and `enabled`
  - `notification_method`: `saved_messages` (default) or `bot`
  - `catch_up`: startup scan settings (`enabled`, `messages_per_source`)
  - `dedup`: `mode`, `only_on_match`, `ttl_days`
  - `notifications`: `snippet_chars`, `bot_chat_id`
  - `logging`: enable console/file logs, rotation, and redaction
- `source_key` format:
  - public usernames: `"@channel_or_group"` (lowercase)
  - any chat by id: `"chat_id:<event.chat_id>"`
  - optional forum topic suffix: `"#topic:<topic_id>"` to monitor a single topic

Examples:
- `"@engineering"`
- `"@engineering#topic:12345"` (single forum topic)
- `"chat_id:123456789#topic:98765"`

For private groups/supergroups you may see `chat_id:-100...` values; telescope accepts both
the raw `chat_id` and the `-100`-prefixed form.

Aliases can be attached to either the base key or a topic-specific key. If you
set a topic alias, notifications will show `base / topic` for clarity.

Logging (optional) example:
```json
"logging": {
  "enabled": true,
  "level": "INFO",
  "console": true,
  "file": {
    "enabled": true,
    "path": "logs/telescope.log",
    "max_bytes": 5242880,
    "backup_count": 5
  },
  "redact": {
    "enabled": true,
    "patterns": ["API_ID", "API_HASH", "BOT_API", "PHONE", "2FA"]
  }
}
```

## Run
```bash
telescope run
```

## Config TUI
Launch the interactive config panel:
```bash
telescope config
```

The TUI lets you edit `config.json` across tabs (Sources, Rules, Settings) and
review stored matches in the Data tab with JSON/CSV export. Save changes with
the on-screen keybindings (see the footer).

Alias:
```bash
telescope setup
```

## Discover archived chats
To list archived group/channel dialogs (useful for finding `chat_id:` values),
run:
```bash
telescope discover
```
This scans **archived** dialogs and prints `source_key` values. If you are not
logged in yet, it will prompt you to authorize first.

## Session login
Telescope uses a **user-session** (not a bot token). On first run it will ask
you to log in and create a local `.session` file for Telethon.

You can choose a login method:
- QR code (default)
- Phone code (SMS/Telegram login code)

If Telegram does not send the SMS/phone code (a known issue with some accounts
and regions), choose the QR code flow instead. It is the most reliable way to
create the session.

Optional env overrides:
- `LOGIN_METHOD=qr` or `LOGIN_METHOD=phone` to skip the prompt.
- `PHONE=+1234567890` to prefill the phone login.
- `2FA=your_password` if your account has a password set.

## Bot notifications (optional)
If you set `notification_method` to `bot` in `config.json`, telescope will send
notifications through the Bot API instead of Saved Messages.
- Set `BOT_API` in `.env` to your bot token.
- Set `notifications.bot_chat_id` in `config.json` to the target chat id.
- Bot notifications use HTML parse mode for reliability (no Markdown errors).

The `discover` command lists **archived** group chats without usernames to help
you discover `chat_id` values to paste into `config.json`. Telescope never
auto-adds chats.

If `catch_up.enabled` is true, telescope will scan the last N messages for any
sources already present in `sources_state` before real-time monitoring begins.

