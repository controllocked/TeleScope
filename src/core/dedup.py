"""Deduplication helpers (core domain)."""

from __future__ import annotations

import hashlib
import re
from typing import Optional


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_fingerprint(text: str) -> str:
    """Normalize text for deterministic fingerprinting."""

    return _collapse_whitespace(text).lower()


def compute_fingerprint(source_key: str, normalized_text: str, mode: str) -> Optional[str]:
    """Return a fingerprint hash based on dedup mode."""

    if mode == "off":
        return None

    if mode == "global":
        payload = normalized_text
    elif mode == "per_source":
        payload = f"{source_key}\n{normalized_text}"
    else:
        raise ValueError(f"Unsupported dedup mode: {mode}")

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
