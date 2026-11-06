import asyncio
from datetime import UTC, datetime

from custom_components.private_find_hub.api.client import UpdateEngine
from custom_components.private_find_hub.api.exceptions import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from custom_components.private_find_hub.api.mock import encode_mock_report
from custom_components.private_find_hub.api.models import (
    ConnectionStatus,
    DeviceRecord,
    EncryptedReport,
)


class PartialFailureAdapter:
    is_mock = True

    def __init__(self, valid: EncryptedReport, invalid: EncryptedReport) -> None:
        self.reports = (valid, invalid)

    async def async_list_devices(self):
        return (DeviceRecord("one", "[MOCK] One"), DeviceRecord("two", "[MOCK] Two"))

    async def async_fetch_reports(self, device_ids):
        return self.reports

    async def async_close(self):
        return None


def test_single_tag_failure_does_not_drop_other_tag() -> None:
    now = datetime.now(UTC)
    first_key = bytes(range(32))
    second_key = bytes(reversed(range(32)))
    valid = encode_mock_report("one", first_key, now, now, 1.0, 2.0, 5.0, "one-1")
    encrypted = encode_mock_report("two", second_key, now, now, 3.0, 4.0, 5.0, "two-1")
    invalid = EncryptedReport(
        device_id=encrypted.device_id,
        observed_at=encrypted.observed_at,
        retrieved_at=encrypted.retrieved_at,
        nonce=encrypted.nonce,
        ciphertext=encrypted.ciphertext[:-1] + bytes([encrypted.ciphertext[-1] ^ 1]),
        accuracy_m=encrypted.accuracy_m,
        source_type=encrypted.source_type,
    )
    engine = UpdateEngine(
        PartialFailureAdapter(valid, invalid),
        {"one": first_key, "two": second_key},
    )
    result = asyncio.run(engine.async_update(frozenset({"one", "two"})))
    assert set(result.fixes) == {"one"}
    assert result.errors == {"two": "DecryptionError"}


def test_missing_key_status_mapping_and_close() -> None:
    now = datetime.now(UTC)
    key = bytes(range(32))
    report = encode_mock_report("one", key, now, now, 1.0, 2.0, 5.0, "one-1")
    adapter = PartialFailureAdapter(report, report)
    engine = UpdateEngine(adapter, {})
    result = asyncio.run(engine.async_update(frozenset({"one"})))
    assert result.errors == {"one": "key_missing"}
    assert (
        engine.status_for_error(AuthenticationRequiredError())
        is ConnectionStatus.AUTHENTICATION_REQUIRED
    )
    assert engine.status_for_error(RateLimitedError()) is ConnectionStatus.RATE_LIMITED
    assert engine.status_for_error(RuntimeError()) is ConnectionStatus.UNAVAILABLE
    asyncio.run(engine.async_close())

