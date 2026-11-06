from __future__ import annotations

import json
import secrets
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .decoder import report_aad
from .models import DeviceRecord, EncryptedReport

MOCK_DEVICES = (
    DeviceRecord("mock-tag-alpha", "[MOCK] Alpha", "Synthetic tag"),
    DeviceRecord("mock-tag-beta", "[MOCK] Beta", "Synthetic tag"),
)

MOCK_COORDINATES = {
    "mock-tag-alpha": (12.345678, 23.456789, 15.0),
    "mock-tag-beta": (-34.56789, 45.678901, 30.0),
}


def create_mock_keys() -> dict[str, bytes]:
    return {device.device_id: secrets.token_bytes(32) for device in MOCK_DEVICES}


def encode_mock_report(
    device_id: str,
    key: bytes,
    observed_at: datetime,
    retrieved_at: datetime,
    latitude: float,
    longitude: float,
    accuracy_m: float | None,
    report_id: str,
) -> EncryptedReport:
    nonce = secrets.token_bytes(12)
    report = EncryptedReport(
        device_id=device_id,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        nonce=nonce,
        ciphertext=b"",
        accuracy_m=accuracy_m,
        source_type="synthetic_mock",
    )
    payload = json.dumps(
        {"latitude": latitude, "longitude": longitude, "report_id": report_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encrypted = AESGCM(key).encrypt(nonce, payload, report_aad(report))
    return EncryptedReport(
        device_id=report.device_id,
        observed_at=report.observed_at,
        retrieved_at=report.retrieved_at,
        nonce=report.nonce,
        ciphertext=encrypted,
        accuracy_m=report.accuracy_m,
        source_type=report.source_type,
    )


class MockFindHubAdapter:
    is_mock = True

    def __init__(self, keys: Mapping[str, bytes]) -> None:
        self._keys = dict(keys)
        self._counter = 0
        self._closed = False

    async def async_list_devices(self) -> Sequence[DeviceRecord]:
        if self._closed:
            return ()
        return MOCK_DEVICES

    async def async_fetch_reports(self, device_ids: frozenset[str]) -> Sequence[EncryptedReport]:
        if self._closed:
            return ()
        now = datetime.now(UTC)
        self._counter += 1
        reports: list[EncryptedReport] = []
        for device_id in sorted(device_ids):
            if device_id not in MOCK_COORDINATES or device_id not in self._keys:
                continue
            latitude, longitude, accuracy = MOCK_COORDINATES[device_id]
            reports.append(
                encode_mock_report(
                    device_id,
                    self._keys[device_id],
                    now,
                    now,
                    latitude,
                    longitude,
                    accuracy,
                    f"mock-{self._counter}-{device_id}",
                )
            )
        return reports

    async def async_close(self) -> None:
        self._closed = True

