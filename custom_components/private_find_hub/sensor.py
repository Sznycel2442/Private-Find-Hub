from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrivateFindHubCoordinator
from .entity import PrivateFindHubEntity

TAG_SENSOR_KINDS = ("last_seen", "location_age", "location_quality", "accuracy")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        PrivateFindHubConnectionSensor(coordinator),
        PrivateFindHubPrivacySensor(coordinator),
        PrivateFindHubErrorCountSensor(coordinator),
    ]
    for device_id in sorted(coordinator.selected_tags):
        entities.extend(
            PrivateFindHubTagSensor(coordinator, device_id, kind)
            for kind in TAG_SENSOR_KINDS
        )
    async_add_entities(entities)


class PrivateFindHubTagSensor(PrivateFindHubEntity, SensorEntity):
    def __init__(
        self,
        coordinator: PrivateFindHubCoordinator,
        device_id: str,
        kind: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        self.kind = kind
        self._attr_translation_key = kind
        self._attr_unique_id = f"{device_id}_{kind}"
        self._attr_suggested_object_id = f"{DOMAIN}_{device_id}_{kind}"
        if kind == "last_seen":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif kind == "location_age":
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        elif kind == "accuracy":
            self._attr_device_class = SensorDeviceClass.DISTANCE
            self._attr_native_unit_of_measurement = UnitOfLength.METERS

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.privacy_open
            and self.fix is not None
        )

    @property
    def native_value(self):
        if not self.privacy_open or self.fix is None:
            return None
        fix = self.fix
        if self.kind == "last_seen":
            return fix.observed_at
        if self.kind == "location_age":
            if fix.observed_at is None:
                return None
            return round(max(0.0, (datetime.now(UTC) - fix.observed_at).total_seconds() / 60), 1)
        if self.kind == "location_quality":
            return fix.quality
        if self.kind == "accuracy":
            return fix.accuracy_m
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"mock": True, "privacy_gate": self.coordinator.data.privacy.state}


class PrivateFindHubHubSensor(CoordinatorEntity[PrivateFindHubCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PrivateFindHubCoordinator, kind: str) -> None:
        super().__init__(coordinator)
        self.kind = kind
        self._attr_translation_key = kind
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{kind}"
        self._attr_suggested_object_id = f"{DOMAIN}_{kind}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            manufacturer="Private Find Hub",
            model="Safe mock prototype",
            name=self.coordinator.entry.title,
        )


class PrivateFindHubConnectionSensor(PrivateFindHubHubSensor):
    def __init__(self, coordinator: PrivateFindHubCoordinator) -> None:
        super().__init__(coordinator, "connection_status")

    @property
    def native_value(self):
        if not self.coordinator.last_update_success:
            return "unavailable"
        return self.coordinator.data.snapshot.connection_status


class PrivateFindHubPrivacySensor(PrivateFindHubHubSensor):
    def __init__(self, coordinator: PrivateFindHubCoordinator) -> None:
        super().__init__(coordinator, "privacy_gate")

    @property
    def native_value(self):
        return self.coordinator.data.privacy.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "checked_entities": self.coordinator.data.privacy.checked_entities,
            "recorder_policy": self.coordinator.data.privacy.recorder_policy,
        }


class PrivateFindHubErrorCountSensor(PrivateFindHubHubSensor):
    def __init__(self, coordinator: PrivateFindHubCoordinator) -> None:
        super().__init__(coordinator, "error_count")

    @property
    def native_value(self):
        return len(self.coordinator.data.snapshot.errors)

