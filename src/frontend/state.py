"""State container for config loading and dirty tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigState:
    data: dict[str, Any] | None = None
    dirty: bool = False
    error: str | None = None
