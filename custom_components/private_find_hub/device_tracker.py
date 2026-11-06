from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MAX_ACCURACY_M,
    DEFAULT_MAX_ACCURACY_M,
    DOMAIN,
)
from .entity import PrivateFindHubEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PrivateFindHubTracker(coordinator, device_id)
        for device_id in sorted(coordinator.selected_tags)
    )


class PrivateFindHubTracker(PrivateFindHubEntity, TrackerEntity):
    _attr_name = None
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_location"
        self._attr_suggested_object_id = f"{DOMAIN}_{device_id}"

    @property
    def _publishable_fix(self):
        if not self.privacy_open:
            return None
        fix = self.fix
        if fix is None:
            return None
        maximum = float(
            self.coordinator.entry.options.get(
                CONF_MAX_ACCURACY_M, DEFAULT_MAX_ACCURACY_M
            )
        )
        if fix.accuracy_m is not None and fix.accuracy_m > maximum:
            return None
        return fix

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.privacy_open
            and self._publishable_fix is not None
        )

    @property
    def latitude(self) -> float | None:
        fix = self._publishable_fix
        return fix.latitude if fix is not None else None

    @property
    def longitude(self) -> float | None:
        fix = self._publishable_fix
        return fix.longitude if fix is not None else None

    @property
    def location_accuracy(self) -> float | None:
        fix = self._publishable_fix
        return fix.accuracy_m if fix is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fix = self._publishable_fix
        if fix is None:
            return {
                "privacy_gate": self.coordinator.data.privacy.state,
                "mock": True,
            }
        return {
            "accuracy_known": fix.accuracy_m is not None,
            "mock": True,
            "observed_at": fix.observed_at.isoformat() if fix.observed_at else None,
            "privacy_gate": self.coordinator.data.privacy.state,
            "quality": fix.quality,
            "retrieved_at": fix.retrieved_at.isoformat(),
            "source_type_detail": fix.source_type,
        }

