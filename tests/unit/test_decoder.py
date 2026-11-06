from datetime import UTC, datetime, timedelta

import pytest

from custom_components.private_find_hub.api.decoder import decode_report
from custom_components.private_find_hub.api.exceptions import DecryptionError
from custom_components.private_find_hub.api.mock import encode_mock_report
from custom_components.private_find_hub.api.models import EncryptedReport, LocationQuality


def test_decode_valid_synthetic_report() -> None:
    key = bytes(range(32))
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    report = encode_mock_report(
        "mock-tag-alpha", key, now, now, 12.5, -45.25, 10.0, "synthetic-1"
    )
    fix = decode_report(report, key, timedelta(hours=1), timedelta(hours=6))
    assert fix.latitude == 12.5
    assert fix.longitude == -45.25
    assert fix.observed_at == now
    assert fix.retrieved_at == now
    assert fix.quality is LocationQuality.FRESH
    assert fix.source_type == "synthetic_mock"
    assert len(fix.report_id) == 24


def test_rejects_modified_aead_tag() -> None:
    key = bytes(range(32))
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    original = encode_mock_report(
        "mock-tag-alpha", key, now, now, 12.5, -45.25, 10.0, "synthetic-1"
    )
    report = EncryptedReport(
        device_id=original.device_id,
        observed_at=original.observed_at,
        retrieved_at=original.retrieved_at,
        nonce=original.nonce,
        ciphertext=original.ciphertext[:-1] + bytes([original.ciphertext[-1] ^ 1]),
        accuracy_m=original.accuracy_m,
        source_type=original.source_type,
    )
    with pytest.raises(DecryptionError, match="authentication_failed"):
        decode_report(report, key, timedelta(hours=1), timedelta(hours=6))

