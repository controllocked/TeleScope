from __future__ import annotations

from core.source_keys import (
    TOPIC_SUFFIX,
    build_effective_source_key,
    expand_source_key_variants,
    split_source_key,
)


def test_build_and_split_source_key_roundtrip() -> None:
    base = "@group"
    assert build_effective_source_key(base, None) == base
    assert build_effective_source_key(base, 123) == f"{base}{TOPIC_SUFFIX}123"

    base_key, topic_id = split_source_key(f"{base}{TOPIC_SUFFIX}123")
    assert base_key == base
    assert topic_id == 123

    base_key, topic_id = split_source_key(base)
    assert base_key == base
    assert topic_id is None


def test_expand_chat_id_variants_positive() -> None:
    variants = expand_source_key_variants("chat_id:123")
    assert "chat_id:123" in variants
    assert "chat_id:-123" in variants
    assert "chat_id:-1000000000123" in variants


def test_expand_chat_id_variants_negative_100() -> None:
    variants = expand_source_key_variants("chat_id:-100987654321")
    assert "chat_id:-100987654321" in variants
    assert "chat_id:987654321" in variants


def test_expand_chat_id_variants_with_topic_suffix() -> None:
    variants = expand_source_key_variants("chat_id:42#topic:7")
    assert "chat_id:42#topic:7" in variants
    assert "chat_id:-42#topic:7" in variants
    assert "chat_id:-1000000000042#topic:7" in variants
