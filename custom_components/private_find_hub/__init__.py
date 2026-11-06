from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from .const import DOMAIN, PLATFORMS
from .security.vault import SecretVault

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import PrivateFindHubCoordinator


@dataclass(slots=True)
class PrivateFindHubRuntimeData:
    coordinator: PrivateFindHubCoordinator
    vault: SecretVault


def vault_path(hass: HomeAssistant, vault_id: str) -> Path:
    try:
        normalized = UUID(vault_id).hex
    except (ValueError, AttributeError) as err:
        raise ValueError("vault_id_invalid") from err
    if normalized != vault_id:
        raise ValueError("vault_id_invalid")
    return Path(hass.config.path(".storage", f"{DOMAIN}_{normalized}.vault"))


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {"vaults": {}})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import PrivateFindHubCoordinator

    domain_data = hass.data.setdefault(DOMAIN, {"vaults": {}})
    vaults = domain_data.setdefault("vaults", {})
    vault_id = str(entry.data["vault_id"])
    vault = vaults.get(entry.entry_id)
    if vault is None:
        vault = SecretVault(vault_path(hass, vault_id))
        vaults[entry.entry_id] = vault
    coordinator = PrivateFindHubCoordinator(hass, entry, vault)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = PrivateFindHubRuntimeData(coordinator, vault)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_request_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.coordinator.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    domain_data = hass.data.get(DOMAIN, {})
    vault = domain_data.get("vaults", {}).pop(entry.entry_id, None)
    if vault is None:
        vault = SecretVault(vault_path(hass, str(entry.data["vault_id"])))
    await hass.async_add_executor_job(vault.destroy)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unlock_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    passphrase: str,
) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {"vaults": {}})
    vaults = domain_data.setdefault("vaults", {})
    vault = vaults.get(entry.entry_id)
    if vault is None:
        vault = SecretVault(vault_path(hass, str(entry.data["vault_id"])))
        vaults[entry.entry_id] = vault
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None:
        await runtime.coordinator.async_unlock(passphrase)
        return
    await hass.async_add_executor_job(vault.unlock, passphrase)


async def async_lock_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None:
        await runtime.coordinator.async_lock()
        return
    vault = hass.data.get(DOMAIN, {}).get("vaults", {}).get(entry.entry_id)
    if vault is not None:
        vault.lock()

