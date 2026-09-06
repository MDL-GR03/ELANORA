"""Authenticated encryption for short-lived secrets stored in outbox payloads."""

import hashlib
import json
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


@dataclass(frozen=True, slots=True)
class EncryptedPayload:
    """Encrypted JSON payload tagged with the key needed to decrypt it."""

    key_id: str
    ciphertext: str


class OutboxKeyRing:
    """Encrypt with the first key and decrypt with retained rotation keys."""

    def __init__(self, encoded_keys: str) -> None:
        keys = [key.strip() for key in encoded_keys.split(",") if key.strip()]
        if not keys:
            raise ValueError("At least one outbox encryption key is required")
        self._keys = {self.key_id(key): Fernet(key.encode("ascii")) for key in keys}
        self._current_id = self.key_id(keys[0])

    @staticmethod
    def key_id(encoded_key: str) -> str:
        """Return a non-secret stable identifier for an encoded key."""
        return hashlib.sha256(encoded_key.encode("ascii")).hexdigest()[:16]

    def encrypt(self, payload: dict[str, object]) -> EncryptedPayload:
        """Encrypt a JSON-compatible payload with the current key."""
        plaintext = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        ciphertext = self._keys[self._current_id].encrypt(plaintext).decode("ascii")
        return EncryptedPayload(key_id=self._current_id, ciphertext=ciphertext)

    def decrypt(self, payload: EncryptedPayload) -> dict[str, object]:
        """Authenticate and decrypt a payload using its recorded key ID."""
        cipher = self._keys.get(payload.key_id)
        if cipher is None:
            raise ValueError(f"Unknown outbox encryption key ID: {payload.key_id}")
        try:
            plaintext = cipher.decrypt(payload.ciphertext.encode("ascii"))
        except InvalidToken as error:
            raise ValueError("Outbox payload authentication failed") from error
        decoded = json.loads(plaintext)
        if not isinstance(decoded, dict):
            raise ValueError("Decrypted outbox payload must be a JSON object")
        return decoded
