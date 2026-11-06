from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import UpdateEngine, UpdatePolicy
from .api.exceptions import AuthenticationRequiredError, RateLimitedError
from .api.mock import MockFindHubAdapter
from .api.models import ConnectionStatus, UpdateSnapshot
from .const import (
    CONF_AGING_MINUTES,
    CONF_FRESH_MINUTES,
    CONF_RECORDER_ACKNOWLEDGED,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SELECTED_TAGS,
    DEFAULT_AGING_MINUTES,
    DEFAULT_FRESH_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from .privacy.gate import PrivacyDecision, PrivacyGate, PrivacyGateState, RecorderPolicy
from .privacy.recorder_checks import check_recorder_policy
from .security.redaction import safe_exception_name
from .security.vault import SecretVault, VaultLockedError, VaultState

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CoordinatorData:
    snapshot: UpdateSnapshot
    privacy: PrivacyDecision
    vault_state: VaultState


def _empty_snapshot(status: ConnectionStatus) -> UpdateSnapshot:
    return UpdateSnapshot({}, {}, {}, status, datetime.now(UTC))


class PrivateFindHubCoordinator(DataUpdateCoordinator[CoordinatorData]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        vault: SecretVault,
    ) -> None:
        self.entry = entry
        self.vault = vault
        self._engine: UpdateEngine | None = None
        self._privacy_gate = PrivacyGate()
        interval = int(entry.options.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
            always_update=True,
        )
        if vault.state is VaultState.UNLOCKED:
            self._engine = self._create_engine()

    @property
    def selected_tags(self) -> frozenset[str]:
        values = self.entry.options.get(CONF_SELECTED_TAGS, ())
        return frozenset(str(item) for item in values)

    async def async_unlock(self, passphrase: str) -> None:
        await self.hass.async_add_executor_job(self.vault.unlock, passphrase)
        self._engine = self._create_engine()
        await self.async_refresh()

    async def async_lock(self) -> None:
        if self._engine is not None:
            await self._engine.async_close()
        self._engine = None
        self.vault.lock()
        self.async_set_updated_data(
            CoordinatorData(
                _empty_snapshot(ConnectionStatus.LOCKED),
                self._privacy_decision(),
                VaultState.LOCKED,
            )
        )

    async def _async_update_data(self) -> CoordinatorData:
        privacy = self._privacy_decision()
        if self.vault.state is VaultState.LOCKED or self._engine is None:
            return CoordinatorData(
                _empty_snapshot(ConnectionStatus.LOCKED),
                privacy,
                VaultState.LOCKED,
            )
        try:
            snapshot = await self._engine.async_update(self.selected_tags)
        except AuthenticationRequiredError as err:
            raise ConfigEntryAuthFailed from err
        except RateLimitedError as err:
            raise UpdateFailed("rate_limited", retry_after=err.retry_after) from err
        except Exception as err:
            raise UpdateFailed(safe_exception_name(err)) from err
        return CoordinatorData(snapshot, privacy, VaultState.UNLOCKED)

    def _privacy_decision(self) -> PrivacyDecision:
        check = check_recorder_policy(self.hass, self.entry.entry_id)
        acknowledged = bool(self.entry.options.get(CONF_RECORDER_ACKNOWLEDGED, False))
        return self._privacy_gate.evaluate(check.policy, acknowledged, len(check.entity_ids))

    def _create_engine(self) -> UpdateEngine:
        encoded_keys = self.vault.get("device_keys")
        if not isinstance(encoded_keys, dict):
            raise VaultLockedError("vault_payload_invalid")
        keys: dict[str, bytes] = {}
        for device_id, encoded in encoded_keys.items():
            if not isinstance(device_id, str) or not isinstance(encoded, str):
                raise VaultLockedError("vault_payload_invalid")
            try:
                key = base64.b64decode(encoded, validate=True)
            except ValueError as err:
                raise VaultLockedError("vault_payload_invalid") from err
            if len(key) != 32:
                raise VaultLockedError("vault_payload_invalid")
            keys[device_id] = key
        policy = UpdatePolicy(
            fresh_for=timedelta(
                minutes=int(self.entry.options.get(CONF_FRESH_MINUTES, DEFAULT_FRESH_MINUTES))
            ),
            aging_for=timedelta(
                minutes=int(self.entry.options.get(CONF_AGING_MINUTES, DEFAULT_AGING_MINUTES))
            ),
        )
        return UpdateEngine(MockFindHubAdapter(keys), keys, policy)

    async def async_shutdown(self) -> None:
        if self._engine is not None:
            await self._engine.async_close()
        self._engine = None
        await super().async_shutdown()


def closed_privacy_decision() -> PrivacyDecision:
    return PrivacyDecision(
        PrivacyGateState.CLOSED_UNVERIFIED,
        False,
        RecorderPolicy.UNVERIFIED,
        0,
    )

