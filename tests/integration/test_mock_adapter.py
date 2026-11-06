import asyncio

from custom_components.private_find_hub.api.client import UpdateEngine
from custom_components.private_find_hub.api.mock import (
    MOCK_DEVICES,
    MockFindHubAdapter,
    create_mock_keys,
)
from custom_components.private_find_hub.api.models import ConnectionStatus


def test_mock_adapter_multiple_tags_and_close() -> None:
    keys = create_mock_keys()
    assert set(keys) == {item.device_id for item in MOCK_DEVICES}
    adapter = MockFindHubAdapter(keys)
    engine = UpdateEngine(adapter, keys)
    selected = frozenset(keys)
    first = asyncio.run(engine.async_update(selected))
    second = asyncio.run(engine.async_update(selected))
    assert set(first.devices) == selected
    assert set(first.fixes) == selected
    assert second.connection_status is ConnectionStatus.MOCK
    assert all(item.source_type == "synthetic_mock" for item in second.fixes.values())
    asyncio.run(engine.async_close())
    assert asyncio.run(adapter.async_list_devices()) == ()
    assert asyncio.run(adapter.async_fetch_reports(selected)) == ()


def test_mock_adapter_skips_unknown_or_keyless_device() -> None:
    adapter = MockFindHubAdapter({})
    reports = asyncio.run(
        adapter.async_fetch_reports(frozenset({"mock-tag-alpha", "unknown"}))
    )
    assert reports == []

