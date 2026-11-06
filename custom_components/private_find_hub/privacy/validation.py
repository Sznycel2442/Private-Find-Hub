from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from ..api.exceptions import InvalidLocationError
from ..api.models import LocationFix, LocationQuality

MAX_FUTURE_SKEW = timedelta(minutes=5)
MAX_ACCURACY_M = 100_000.0


def ensure_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidLocationError(f"{field}_not_utc")
    return value.astimezone(UTC)


def classify_quality(
    observed_at: datetime | None,
    now: datetime,
    fresh_for: timedelta,
    aging_for: timedelta,
) -> LocationQuality:
    if observed_at is None:
        return LocationQuality.UNKNOWN
    observed = ensure_utc(observed_at, "observed_at")
    current = ensure_utc(now, "now")
    if observed > current + MAX_FUTURE_SKEW:
        return LocationQuality.UNKNOWN
    age = max(current - observed, timedelta())
    if age <= fresh_for:
        return LocationQuality.FRESH
    if age <= aging_for:
        return LocationQuality.AGING
    return LocationQuality.STALE


def validate_fix(
    fix: LocationFix,
    now: datetime,
    fresh_for: timedelta,
    aging_for: timedelta,
) -> LocationFix:
    if not fix.device_id.strip():
        raise InvalidLocationError("device_id_missing")
    if not math.isfinite(fix.latitude) or not -90.0 <= fix.latitude <= 90.0:
        raise InvalidLocationError("latitude_invalid")
    if not math.isfinite(fix.longitude) or not -180.0 <= fix.longitude <= 180.0:
        raise InvalidLocationError("longitude_invalid")
    if fix.observed_at is not None:
        observed = ensure_utc(fix.observed_at, "observed_at")
        if observed > ensure_utc(now, "now") + MAX_FUTURE_SKEW:
            raise InvalidLocationError("observed_at_future")
    ensure_utc(fix.retrieved_at, "retrieved_at")
    if fix.accuracy_m is not None:
        if not math.isfinite(fix.accuracy_m) or not 0.0 <= fix.accuracy_m <= MAX_ACCURACY_M:
            raise InvalidLocationError("accuracy_invalid")
    quality = classify_quality(fix.observed_at, now, fresh_for, aging_for)
    return fix.with_quality(quality)


def should_replace(current: LocationFix | None, incoming: LocationFix) -> bool:
    if current is None:
        return True
    if incoming.report_id == current.report_id:
        return False
    if incoming.observed_at is None:
        return current.observed_at is None and incoming.retrieved_at > current.retrieved_at
    if current.observed_at is None:
        return True
    return incoming.observed_at > current.observed_at

