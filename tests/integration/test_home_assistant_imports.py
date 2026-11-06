import importlib.util

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("homeassistant") is None,
    reason="Home Assistant is verified by the Python 3.14 CI job",
)
def test_home_assistant_modules_import() -> None:
    from custom_components.private_find_hub import (
        config_flow,
        device_tracker,
        diagnostics,
        repairs,
        sensor,
    )

    assert config_flow.PrivateFindHubConfigFlow.VERSION == 1
    assert callable(device_tracker.async_setup_entry)
    assert callable(sensor.async_setup_entry)
    assert callable(diagnostics.async_get_config_entry_diagnostics)
    assert callable(repairs.async_create_fix_flow)
