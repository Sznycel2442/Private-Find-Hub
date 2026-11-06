import asyncio

import pytest

from custom_components.private_find_hub.api.exceptions import ProtocolBlockedError
from custom_components.private_find_hub.api.transport import BlockedGoogleAdapter


def test_google_adapter_is_blocked_without_network() -> None:
    adapter = BlockedGoogleAdapter()
    with pytest.raises(ProtocolBlockedError, match="feasibility_audit"):
        asyncio.run(adapter.async_list_devices())
