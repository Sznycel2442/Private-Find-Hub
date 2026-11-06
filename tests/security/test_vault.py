import json
from pathlib import Path

import pytest

from custom_components.private_find_hub.security.vault import (
    SecretVault,
    VaultAuthenticationError,
    VaultError,
    VaultLockedError,
    VaultState,
)

PASSPHRASE = "correct horse battery staple"


def payload() -> dict[str, object]:
    return {
        "adapter": "mock",
        "device_keys": {"mock-tag-alpha": "c3ludGhldGljLWtleQ=="},
        "refresh_token": "synthetic-token-not-google",
    }


def test_vault_is_locked_after_create_and_contains_no_plaintext(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    vault = SecretVault(path)
    vault.create(PASSPHRASE, "vault-one", payload())
    assert vault.state is VaultState.LOCKED
    raw = path.read_text(encoding="utf-8")
    assert PASSPHRASE not in raw
    assert "synthetic-token-not-google" not in raw
    assert "device_keys" not in raw
    assert vault.metadata().vault_id == "vault-one"


def test_unlock_and_lock(tmp_path: Path) -> None:
    vault = SecretVault(tmp_path / "vault.json")
    vault.create(PASSPHRASE, "vault-one", payload())
    assert vault.unlock(PASSPHRASE) == payload()
    assert vault.get("adapter") == "mock"
    vault.lock()
    with pytest.raises(VaultLockedError):
        vault.get("adapter")


def test_wrong_passphrase_does_not_unlock(tmp_path: Path) -> None:
    vault = SecretVault(tmp_path / "vault.json")
    vault.create(PASSPHRASE, "vault-one", payload())
    with pytest.raises(VaultAuthenticationError, match="vault_unlock_failed"):
        vault.unlock("wrong password that is long")
    assert vault.state is VaultState.LOCKED


def test_modified_ciphertext_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    vault = SecretVault(path)
    vault.create(PASSPHRASE, "vault-one", payload())
    document = json.loads(path.read_text(encoding="utf-8"))
    ciphertext = document["cipher"]["ciphertext"]
    document["cipher"]["ciphertext"] = ciphertext[:-2] + "AA"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises((VaultAuthenticationError, VaultError)):
        vault.unlock(PASSPHRASE)


def test_rotation_invalidates_old_passphrase(tmp_path: Path) -> None:
    vault = SecretVault(tmp_path / "vault.json")
    vault.create(PASSPHRASE, "vault-one", payload())
    vault.rotate(PASSPHRASE, "another long private passphrase")
    with pytest.raises(VaultAuthenticationError):
        vault.unlock(PASSPHRASE)
    assert vault.unlock("another long private passphrase") == payload()


def test_location_fields_cannot_be_written_to_vault(tmp_path: Path) -> None:
    vault = SecretVault(tmp_path / "vault.json")
    with pytest.raises(VaultError, match="location_data_forbidden"):
        vault.create(PASSPHRASE, "vault-one", {"latitude": 1.0})


def test_vault_rejects_bad_inputs_and_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    vault = SecretVault(path)
    with pytest.raises(VaultError, match="passphrase_too_short"):
        vault.create("short", "vault-one", payload())
    with pytest.raises(VaultError, match="vault_id_invalid"):
        vault.create(PASSPHRASE, "", payload())
    with pytest.raises(VaultError, match="secret_key_invalid"):
        vault.create(PASSPHRASE, "vault-one", {1: "bad"})
    vault.create(PASSPHRASE, "vault-one", payload())
    with pytest.raises(VaultError, match="vault_exists"):
        vault.create(PASSPHRASE, "vault-two", payload())


def test_vault_corruption_destroy_and_missing_destroy(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    path.write_text("{}", encoding="utf-8")
    vault = SecretVault(path)
    with pytest.raises(VaultError, match="vault_version_unsupported"):
        vault.metadata()
    assert vault.destroy()
    assert not vault.destroy()

