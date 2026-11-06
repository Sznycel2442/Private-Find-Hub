from __future__ import annotations

import base64
import json
import os
import secrets
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT_VERSION = 1
MAX_VAULT_BYTES = 1_048_576
ARGON2_TIME_COST = 3
ARGON2_MEMORY_KIB = 65_536
ARGON2_PARALLELISM = 1
KEY_LENGTH = 32
NONCE_LENGTH = 12
MIN_PASSPHRASE_LENGTH = 12
FORBIDDEN_FIELDS = frozenset(
    {"latitude", "longitude", "coordinates", "location", "locations", "fix", "fixes", "history"}
)


class VaultError(Exception):
    pass


class VaultAuthenticationError(VaultError):
    pass


class VaultCorruptedError(VaultError):
    pass


class VaultLockedError(VaultError):
    pass


class VaultState(StrEnum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


@dataclass(frozen=True, slots=True)
class VaultMetadata:
    vault_id: str
    version: int
    created_at: datetime


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: Any, expected_length: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise VaultCorruptedError("vault_invalid")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as err:
        raise VaultCorruptedError("vault_invalid") from err
    if expected_length is not None and len(decoded) != expected_length:
        raise VaultCorruptedError("vault_invalid")
    return decoded


def _validate_secret_shape(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise VaultError("secret_key_invalid")
            if key.casefold() in FORBIDDEN_FIELDS:
                raise VaultError("location_data_forbidden")
            _validate_secret_shape(child, (*path, key))
        return
    if isinstance(value, list):
        for item in value:
            _validate_secret_shape(item, path)
        return
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise VaultError("secret_value_invalid")


class SecretVault:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, Any] | None = None

    @property
    def state(self) -> VaultState:
        return VaultState.UNLOCKED if self._data is not None else VaultState.LOCKED

    @property
    def path(self) -> Path:
        return self._path

    def create(self, passphrase: str, vault_id: str, payload: Mapping[str, Any]) -> VaultMetadata:
        if self._path.exists():
            raise VaultError("vault_exists")
        self._validate_passphrase(passphrase)
        if not vault_id or len(vault_id) > 128:
            raise VaultError("vault_id_invalid")
        material = dict(payload)
        _validate_secret_shape(material)
        created_at = datetime.now(UTC)
        envelope = self._encrypt(passphrase, vault_id, created_at, material)
        self._atomic_write(envelope)
        self._data = None
        return VaultMetadata(vault_id, VAULT_VERSION, created_at)

    def metadata(self) -> VaultMetadata:
        envelope = self._load_envelope()
        return self._parse_metadata(envelope)

    def unlock(self, passphrase: str) -> Mapping[str, Any]:
        envelope = self._load_envelope()
        metadata = self._parse_metadata(envelope)
        kdf = envelope.get("kdf")
        cipher = envelope.get("cipher")
        if not isinstance(kdf, dict) or not isinstance(cipher, dict):
            raise VaultCorruptedError("vault_invalid")
        if kdf.get("name") != "argon2id" or cipher.get("name") != "aes-256-gcm":
            raise VaultCorruptedError("vault_invalid")
        time_cost = self._bounded_int(kdf.get("time_cost"), 2, 10)
        memory_cost = self._bounded_int(kdf.get("memory_cost_kib"), 32_768, 262_144)
        parallelism = self._bounded_int(kdf.get("parallelism"), 1, 4)
        salt = _b64decode(kdf.get("salt"), 16)
        nonce = _b64decode(cipher.get("nonce"), NONCE_LENGTH)
        ciphertext = _b64decode(cipher.get("ciphertext"))
        if len(ciphertext) < 17:
            raise VaultCorruptedError("vault_invalid")
        key = self._derive_key(passphrase, salt, time_cost, memory_cost, parallelism)
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, self._aad(metadata.vault_id))
        except InvalidTag as err:
            raise VaultAuthenticationError("vault_unlock_failed") from err
        finally:
            mutable_key = bytearray(key)
            mutable_key[:] = b"\0" * len(mutable_key)
        try:
            data = json.loads(plaintext)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise VaultCorruptedError("vault_invalid") from err
        if not isinstance(data, dict):
            raise VaultCorruptedError("vault_invalid")
        _validate_secret_shape(data)
        self._data = data
        return dict(data)

    def lock(self) -> None:
        self._data = None

    def get(self, key: str) -> Any:
        if self._data is None:
            raise VaultLockedError("vault_locked")
        return self._data.get(key)

    def rotate(self, old_passphrase: str, new_passphrase: str) -> None:
        data = dict(self.unlock(old_passphrase))
        self._validate_passphrase(new_passphrase)
        metadata = self.metadata()
        envelope = self._encrypt(new_passphrase, metadata.vault_id, metadata.created_at, data)
        self._atomic_write(envelope)
        self._data = None

    def destroy(self) -> bool:
        self.lock()
        try:
            self._path.unlink()
        except FileNotFoundError:
            return False
        return True

    def _encrypt(
        self,
        passphrase: str,
        vault_id: str,
        created_at: datetime,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(NONCE_LENGTH)
        key = self._derive_key(
            passphrase,
            salt,
            ARGON2_TIME_COST,
            ARGON2_MEMORY_KIB,
            ARGON2_PARALLELISM,
        )
        plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        try:
            ciphertext = AESGCM(key).encrypt(nonce, plaintext, self._aad(vault_id))
        finally:
            mutable_key = bytearray(key)
            mutable_key[:] = b"\0" * len(mutable_key)
        return {
            "cipher": {
                "ciphertext": _b64encode(ciphertext),
                "name": "aes-256-gcm",
                "nonce": _b64encode(nonce),
            },
            "created_at": created_at.isoformat(),
            "kdf": {
                "memory_cost_kib": ARGON2_MEMORY_KIB,
                "name": "argon2id",
                "parallelism": ARGON2_PARALLELISM,
                "salt": _b64encode(salt),
                "time_cost": ARGON2_TIME_COST,
            },
            "vault_id": vault_id,
            "version": VAULT_VERSION,
        }

    def _atomic_write(self, envelope: Mapping[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode()
        if len(encoded) > MAX_VAULT_BYTES:
            raise VaultError("vault_too_large")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(temporary, self._path)
            temporary = None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _load_envelope(self) -> dict[str, Any]:
        try:
            if self._path.is_symlink():
                raise VaultCorruptedError("vault_invalid")
            size = self._path.stat().st_size
            if size <= 0 or size > MAX_VAULT_BYTES:
                raise VaultCorruptedError("vault_invalid")
            raw = self._path.read_bytes()
            envelope = json.loads(raw)
        except VaultCorruptedError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
            raise VaultCorruptedError("vault_invalid") from err
        if not isinstance(envelope, dict):
            raise VaultCorruptedError("vault_invalid")
        return envelope

    def _parse_metadata(self, envelope: Mapping[str, Any]) -> VaultMetadata:
        if envelope.get("version") != VAULT_VERSION:
            raise VaultCorruptedError("vault_version_unsupported")
        vault_id = envelope.get("vault_id")
        created = envelope.get("created_at")
        if not isinstance(vault_id, str) or not vault_id or not isinstance(created, str):
            raise VaultCorruptedError("vault_invalid")
        try:
            created_at = datetime.fromisoformat(created)
        except ValueError as err:
            raise VaultCorruptedError("vault_invalid") from err
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise VaultCorruptedError("vault_invalid")
        return VaultMetadata(vault_id, VAULT_VERSION, created_at.astimezone(UTC))

    @staticmethod
    def _derive_key(
        passphrase: str,
        salt: bytes,
        time_cost: int,
        memory_cost: int,
        parallelism: int,
    ) -> bytes:
        if not isinstance(passphrase, str):
            raise VaultAuthenticationError("vault_unlock_failed")
        return hash_secret_raw(
            passphrase.encode("utf-8"),
            salt,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=KEY_LENGTH,
            type=Type.ID,
        )

    @staticmethod
    def _validate_passphrase(passphrase: str) -> None:
        if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE_LENGTH:
            raise VaultError("passphrase_too_short")

    @staticmethod
    def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise VaultCorruptedError("vault_invalid")
        return value

    @staticmethod
    def _aad(vault_id: str) -> bytes:
        return f"private_find_hub:v{VAULT_VERSION}:{vault_id}".encode()

