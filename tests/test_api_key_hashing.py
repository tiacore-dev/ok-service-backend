import hashlib
import re

from app.domain.api_keys import (
    API_KEY_HASH_LENGTH,
    generate_raw_api_key,
    hash_api_key,
)


def test_hash_api_key_is_deterministic_sha256_hex():
    assert hash_api_key("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert hash_api_key("abc") == hash_api_key("abc")
    assert hash_api_key("abc") != hash_api_key("abd")


def test_hash_api_key_never_returns_plaintext():
    raw = generate_raw_api_key()
    digest = hash_api_key(raw)

    assert digest != raw
    assert raw not in digest
    assert len(digest) == API_KEY_HASH_LENGTH
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_hash_api_key_encodes_utf8_like_postgres_convert_to():
    raw = "ключ-🔑"
    assert hash_api_key(raw) == hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_generate_raw_api_key_is_random_and_url_safe():
    keys = {generate_raw_api_key() for _ in range(50)}

    assert len(keys) == 50
    for key in keys:
        assert len(key) == 64  # token_urlsafe(48) -> 64 base64url characters
        assert re.fullmatch(r"[A-Za-z0-9_-]+", key)
