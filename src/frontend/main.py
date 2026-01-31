"""Entry point for the Textual config panel."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from frontend.app import ConfigPanelApp  # noqa: E402


if __name__ == "__main__":
    ConfigPanelApp().run()
