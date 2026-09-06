"""Authenticated encryption and key rotation for outbox secrets."""

import json

import pytest
from cryptography.fernet import Fernet

from app.core.outbox_crypto import EncryptedPayload, OutboxKeyRing


def test_payload_round_trip_does_not_expose_plaintext() -> None:
    key = Fernet.generate_key().decode("ascii")
    key_ring = OutboxKeyRing(key)
    source = {"email": "researcher@example.org", "code": "123456"}

    encrypted = key_ring.encrypt(source)

    assert "123456" not in encrypted.ciphertext
    assert key_ring.decrypt(encrypted) == source


def test_key_rotation_retains_decryption_of_queued_events() -> None:
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    old_ring = OutboxKeyRing(old_key)
    encrypted = old_ring.encrypt({"code": "654321"})

    rotated_ring = OutboxKeyRing(f"{new_key},{old_key}")

    assert rotated_ring.decrypt(encrypted) == {"code": "654321"}
    assert rotated_ring.encrypt({"code": "new"}).key_id != encrypted.key_id


def test_tampered_ciphertext_is_rejected() -> None:
    key = Fernet.generate_key().decode("ascii")
    key_ring = OutboxKeyRing(key)
    encrypted = key_ring.encrypt({"code": "123456"})
    tampered = EncryptedPayload(
        key_id=encrypted.key_id,
        ciphertext=encrypted.ciphertext[:-2] + "AA",
    )

    with pytest.raises(ValueError, match="authentication failed"):
        key_ring.decrypt(tampered)


def test_decrypted_payload_must_be_an_object() -> None:
    key = Fernet.generate_key().decode("ascii")
    key_ring = OutboxKeyRing(key)
    cipher = Fernet(key.encode("ascii"))
    encrypted = EncryptedPayload(
        key_id=OutboxKeyRing.key_id(key),
        ciphertext=cipher.encrypt(json.dumps(["invalid"]).encode()).decode(),
    )

    with pytest.raises(ValueError, match="JSON object"):
        key_ring.decrypt(encrypted)
