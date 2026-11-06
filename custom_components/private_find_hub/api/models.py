from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class LocationQuality(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    AUTHENTICATION_REQUIRED = "authentication_required"
    LOCKED = "locked"
    MOCK = "mock"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DeviceRecord:
    device_id: str
    name: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class EncryptedReport:
    device_id: str
    observed_at: datetime | None
    retrieved_at: datetime
    nonce: bytes
    ciphertext: bytes
    accuracy_m: float | None
    source_type: str


@dataclass(frozen=True, slots=True)
class LocationFix:
    device_id: str
    latitude: float
    longitude: float
    observed_at: datetime | None
    retrieved_at: datetime
    accuracy_m: float | None
    source_type: str
    quality: LocationQuality
    report_id: str

    def with_quality(self, quality: LocationQuality) -> LocationFix:
        return replace(self, quality=quality)


@dataclass(frozen=True, slots=True)
class UpdateSnapshot:
    devices: dict[str, DeviceRecord]
    fixes: dict[str, LocationFix]
    errors: dict[str, str]
    connection_status: ConnectionStatus
    retrieved_at: datetime

