from datetime import UTC, datetime, timedelta

import pytest

from custom_components.private_find_hub.api.exceptions import InvalidLocationError
from custom_components.private_find_hub.api.models import LocationFix, LocationQuality
from custom_components.private_find_hub.privacy.validation import should_replace, validate_fix


def make_fix(
    observed_at: datetime | None,
    latitude: float = 1.0,
    report_id: str = "report",
) -> LocationFix:
    return LocationFix(
        device_id="tag",
        latitude=latitude,
        longitude=2.0,
        observed_at=observed_at,
        retrieved_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        accuracy_m=10.0,
        source_type="synthetic_mock",
        quality=LocationQuality.UNKNOWN,
        report_id=report_id,
    )


@pytest.mark.parametrize("latitude", [float("nan"), float("inf"), -91.0, 91.0])
def test_rejects_invalid_latitude(latitude: float) -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    with pytest.raises(InvalidLocationError, match="latitude_invalid"):
        validate_fix(make_fix(now, latitude), now, timedelta(hours=1), timedelta(hours=6))


def test_rejects_future_timestamp() -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    with pytest.raises(InvalidLocationError, match="observed_at_future"):
        validate_fix(
            make_fix(now + timedelta(minutes=6)),
            now,
            timedelta(hours=1),
            timedelta(hours=6),
        )


def test_missing_observation_is_unknown() -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    fix = validate_fix(make_fix(None), now, timedelta(hours=1), timedelta(hours=6))
    assert fix.quality is LocationQuality.UNKNOWN


def test_older_fix_does_not_replace_newer() -> None:
    current = make_fix(datetime(2026, 11, 6, 11, 0, tzinfo=UTC), report_id="new")
    incoming = make_fix(datetime(2026, 11, 6, 10, 0, tzinfo=UTC), report_id="old")
    assert should_replace(current, incoming) is False


@pytest.mark.parametrize("longitude", [float("nan"), float("inf"), -181.0, 181.0])
def test_rejects_invalid_longitude(longitude: float) -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    fix = make_fix(now)
    fix = fix.__class__(
        device_id=fix.device_id,
        latitude=fix.latitude,
        longitude=longitude,
        observed_at=fix.observed_at,
        retrieved_at=fix.retrieved_at,
        accuracy_m=fix.accuracy_m,
        source_type=fix.source_type,
        quality=fix.quality,
        report_id=fix.report_id,
    )
    with pytest.raises(InvalidLocationError, match="longitude_invalid"):
        validate_fix(fix, now, timedelta(hours=1), timedelta(hours=6))


def test_replacement_and_quality_paths() -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    fresh = validate_fix(make_fix(now), now, timedelta(hours=1), timedelta(hours=6))
    assert fresh.quality is LocationQuality.FRESH
    aging = make_fix(now - timedelta(hours=2), report_id="aging")
    stale = make_fix(now - timedelta(hours=7), report_id="stale")
    validated_aging = validate_fix(aging, now, timedelta(hours=1), timedelta(hours=6))
    validated_stale = validate_fix(stale, now, timedelta(hours=1), timedelta(hours=6))
    assert validated_aging.quality is LocationQuality.AGING
    assert validated_stale.quality is LocationQuality.STALE
    assert should_replace(None, aging)
    assert not should_replace(aging, aging)
    assert should_replace(make_fix(None, report_id="none"), aging)


def test_rejects_missing_id_bad_accuracy_and_naive_time() -> None:
    now = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    base = make_fix(now)
    for change, error in (
        ({"device_id": " "}, "device_id_missing"),
        ({"accuracy_m": -1.0}, "accuracy_invalid"),
        ({"retrieved_at": datetime(2026, 11, 6, 12, 0)}, "retrieved_at_not_utc"),
    ):
        values = {name: getattr(base, name) for name in base.__dataclass_fields__}
        values.update(change)
        with pytest.raises(InvalidLocationError, match=error):
            validate_fix(LocationFix(**values), now, timedelta(hours=1), timedelta(hours=6))

