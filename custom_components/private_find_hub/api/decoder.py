from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..privacy.validation import validate_fix
from .exceptions import DecryptionError, InvalidLocationError, ProtocolChangedError
from .models import EncryptedReport, LocationFix, LocationQuality

REPORT_VERSION = 1


def report_aad(report: EncryptedReport) -> bytes:
    observed = report.observed_at.isoformat() if report.observed_at else None
    value = {
        "accuracy_m": report.accuracy_m,
        "device_id": report.device_id,
        "observed_at": observed,
        "source_type": report.source_type,
        "version": REPORT_VERSION,
    }
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def decode_report(
    report: EncryptedReport,
    key: bytes,
    fresh_for: timedelta,
    aging_for: timedelta,
) -> LocationFix:
    if len(key) != 32 or len(report.nonce) != 12:
        raise DecryptionError("invalid_key_material")
    try:
        plaintext = AESGCM(key).decrypt(report.nonce, report.ciphertext, report_aad(report))
    except InvalidTag as err:
        raise DecryptionError("authentication_failed") from err
    try:
        payload: Any = json.loads(plaintext)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ProtocolChangedError("invalid_report_payload") from err
    if not isinstance(payload, dict) or set(payload) != {"latitude", "longitude", "report_id"}:
        raise ProtocolChangedError("unknown_report_schema")
    if not isinstance(payload["report_id"], str) or not payload["report_id"]:
        raise ProtocolChangedError("invalid_report_id")
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (TypeError, ValueError) as err:
        raise InvalidLocationError("coordinates_invalid") from err
    report_id = hashlib.sha256(
        f"{report.device_id}\0{payload['report_id']}".encode()
    ).hexdigest()[:24]
    fix = LocationFix(
        device_id=report.device_id,
        latitude=latitude,
        longitude=longitude,
        observed_at=report.observed_at,
        retrieved_at=report.retrieved_at,
        accuracy_m=report.accuracy_m,
        source_type=report.source_type,
        quality=LocationQuality.UNKNOWN,
        report_id=report_id,
    )
    return validate_fix(fix, report.retrieved_at, fresh_for, aging_for)

