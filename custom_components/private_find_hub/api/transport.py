from __future__ import annotations

from collections.abc import Sequence

from .exceptions import ProtocolBlockedError
from .models import DeviceRecord, EncryptedReport


class BlockedGoogleAdapter:
    is_mock = False

    async def async_list_devices(self) -> Sequence[DeviceRecord]:
        raise ProtocolBlockedError("google_adapter_blocked_by_feasibility_audit")

    async def async_fetch_reports(
        self, device_ids: frozenset[str]
    ) -> Sequence[EncryptedReport]:
        raise ProtocolBlockedError("google_adapter_blocked_by_feasibility_audit")

    async def async_close(self) -> None:
        return None
