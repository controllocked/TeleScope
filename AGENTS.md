# Repository Guidelines

## Project Structure & Module Organization
- `src/core/`: domain logic (rules engine, dedup, processing); keep this layer free of Telegram/SQLite specifics.
- `src/adapters/`: integration code for Telegram mapping/notifications and SQLite storage.
- `src/app.py`: CLI entrypoint and wiring; `src/client.py` owns the Telethon lifecycle.
- `src/frontend/`: optional UI/utility helpers.
- `tests/`: pytest suite, with shared fixtures in `tests/conftest.py`.
- Root config/state: `config.json`, `.env`/`.env.example`, and `logs/`.

## Build, Test, and Development Commands
- `python -m venv .venv` + `source .venv/bin/activate`: create and activate a local virtualenv.
- `pip install -r requirements.txt` and `pip install -e .`: install dependencies and the editable package.
- `telescope run`: start the watcher using `.env` and `config.json`.
- `pytest`: run the test suite.

## Coding Style & Naming Conventions
- Python 3.10+; use 4-space indentation and PEP 8 conventions.
- Prefer type hints for public functions and data structures.
- Naming: `snake_case` for functions/variables, `CapWords` for classes, lowercase module filenames.
- Keep core logic in `src/core/` reusable; adapter-specific code belongs in `src/adapters/`.

## Testing Guidelines
- Framework: `pytest`.
- Test files follow `test_*.py`; test functions start with `test_`.
- No explicit coverage threshold is defined; aim to cover new behavior and edge cases.

## Commit & Pull Request Guidelines
- Commit messages follow a Conventional-Commit style (e.g., `feat:`, `fix:`, `refactor:`, `build(scope):`, `docs:`). Use `!` for breaking changes.
- PRs should include a short summary, testing notes (e.g., `pytest`), and any config or env changes. Add screenshots/log snippets only if behavior is user-visible.

## Configuration & Secrets
- Copy `.env.example` to `.env` and fill `API_ID`, `API_HASH`, and optional `BOT_API`/`2FA`.
- Local state files (`*.session`, `*.db`) and logs are gitignored; avoid committing or sharing them.

Use context7 when working on frontend/CLI features.
