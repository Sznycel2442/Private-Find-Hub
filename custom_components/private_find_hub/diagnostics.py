from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict:
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    return {
        "adapter": entry.data.get("adapter"),
        "connection_status": data.snapshot.connection_status,
        "error_classes": sorted(set(data.snapshot.errors.values())),
        "failed_tag_count": len(data.snapshot.errors),
        "privacy_gate": data.privacy.state,
        "recorder_policy": data.privacy.recorder_policy,
        "selected_tag_count": len(coordinator.selected_tags),
        "vault_state": data.vault_state,
        "version": "0.1.0-alpha.1",
    }

