from __future__ import annotations

from dataclasses import dataclass

from .gate import RecorderPolicy


@dataclass(frozen=True, slots=True)
class RecorderCheck:
    policy: RecorderPolicy
    entity_ids: tuple[str, ...]


def check_recorder_policy(hass, entry_id: str) -> RecorderCheck:
    if "recorder" not in hass.config.components:
        return RecorderCheck(RecorderPolicy.VERIFIED_EXCLUDED, ())
    try:
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        entity_ids = tuple(
            sorted(
                item.entity_id
                for item in registry.entities.values()
                if item.config_entry_id == entry_id and item.platform == "private_find_hub"
            )
        )
    except (AttributeError, KeyError, RuntimeError):
        return RecorderCheck(RecorderPolicy.UNVERIFIED, ())
    if not entity_ids:
        return RecorderCheck(RecorderPolicy.UNVERIFIED, ())
    try:
        from homeassistant.components.recorder import is_entity_recorded

        if any(is_entity_recorded(hass, entity_id) for entity_id in entity_ids):
            return RecorderCheck(RecorderPolicy.INCLUDED, entity_ids)
        return RecorderCheck(RecorderPolicy.VERIFIED_EXCLUDED, entity_ids)
    except (AttributeError, KeyError, RuntimeError):
        return RecorderCheck(RecorderPolicy.UNVERIFIED, entity_ids)

