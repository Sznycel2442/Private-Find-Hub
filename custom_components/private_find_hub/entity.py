from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrivateFindHubCoordinator


class PrivateFindHubEntity(CoordinatorEntity[PrivateFindHubCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: PrivateFindHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.data.snapshot.devices.get(self.device_id)
        name = device.name if device is not None else f"[MOCK] {self.device_id}"
        model = device.model if device is not None else "Synthetic tag"
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer="Private Find Hub",
            model=model,
            name=name,
        )

    @property
    def fix(self):
        return self.coordinator.data.snapshot.fixes.get(self.device_id)

    @property
    def privacy_open(self) -> bool:
        return self.coordinator.data.privacy.can_publish

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self.coordinator.async_request_refresh()

