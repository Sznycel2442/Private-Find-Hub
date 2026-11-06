from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from ..privacy.validation import classify_quality, should_replace
from .decoder import decode_report
from .exceptions import (
    AuthenticationRequiredError,
    DecryptionError,
    InvalidLocationError,
    ProtocolChangedError,
    RateLimitedError,
)
from .models import ConnectionStatus, DeviceRecord, EncryptedReport, LocationFix, UpdateSnapshot


class FindHubAdapter(Protocol):
    is_mock: bool

    async def async_list_devices(self) -> Sequence[DeviceRecord]: ...

    async def async_fetch_reports(
        self, device_ids: frozenset[str]
    ) -> Sequence[EncryptedReport]: ...

    async def async_close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class UpdatePolicy:
    fresh_for: timedelta = timedelta(minutes=60)
    aging_for: timedelta = timedelta(hours=6)


class UpdateEngine:
    def __init__(
        self,
        adapter: FindHubAdapter,
        keys: Mapping[str, bytes],
        policy: UpdatePolicy | None = None,
    ) -> None:
        self._adapter = adapter
        self._keys = dict(keys)
        self._policy = policy or UpdatePolicy()
        self._fixes: dict[str, LocationFix] = {}

    async def async_update(self, selected: frozenset[str]) -> UpdateSnapshot:
        now = datetime.now(UTC)
        devices = {item.device_id: item for item in await self._adapter.async_list_devices()}
        reports = await self._adapter.async_fetch_reports(selected)
        errors: dict[str, str] = {}
        for report in reports:
            if report.device_id not in selected:
                continue
            key = self._keys.get(report.device_id)
            if key is None:
                errors[report.device_id] = "key_missing"
                continue
            try:
                fix = decode_report(
                    report,
                    key,
                    self._policy.fresh_for,
                    self._policy.aging_for,
                )
            except (DecryptionError, InvalidLocationError, ProtocolChangedError) as err:
                errors[report.device_id] = type(err).__name__
                continue
            if should_replace(self._fixes.get(fix.device_id), fix):
                self._fixes[fix.device_id] = fix
        refreshed: dict[str, LocationFix] = {}
        for device_id, fix in self._fixes.items():
            if device_id not in selected:
                continue
            quality = classify_quality(
                fix.observed_at,
                now,
                self._policy.fresh_for,
                self._policy.aging_for,
            )
            refreshed[device_id] = fix.with_quality(quality)
        return UpdateSnapshot(
            devices={key: value for key, value in devices.items() if key in selected},
            fixes=refreshed,
            errors=errors,
            connection_status=(
                ConnectionStatus.MOCK
                if self._adapter.is_mock
                else ConnectionStatus.CONNECTED
            ),
            retrieved_at=now,
        )

    def status_for_error(self, err: Exception) -> ConnectionStatus:
        if isinstance(err, AuthenticationRequiredError):
            return ConnectionStatus.AUTHENTICATION_REQUIRED
        if isinstance(err, RateLimitedError):
            return ConnectionStatus.RATE_LIMITED
        return ConnectionStatus.UNAVAILABLE

    async def async_close(self) -> None:
        await self._adapter.async_close()

