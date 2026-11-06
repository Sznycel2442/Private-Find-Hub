import pytest

from custom_components.private_find_hub.api.exceptions import NetworkPolicyError
from custom_components.private_find_hub.security.network_policy import (
    validate_https_url,
    validate_redirect,
)


def test_all_runtime_egress_is_denied_in_mock_build() -> None:
    with pytest.raises(NetworkPolicyError, match="host_forbidden"):
        validate_https_url("https://example.com/path")


@pytest.mark.parametrize(
    "url,error",
    [
        ("http://allowed.example/path", "https_required"),
        ("https://user:pass@allowed.example/path", "userinfo_forbidden"),
        ("https://127.0.0.1/path", "ip_literal_forbidden"),
        ("https://allowed.example:444/path", "port_forbidden"),
    ],
)
def test_rejects_unsafe_url(url: str, error: str) -> None:
    with pytest.raises(NetworkPolicyError, match=error):
        validate_https_url(url, {"allowed.example"})


def test_redirect_target_is_revalidated() -> None:
    with pytest.raises(NetworkPolicyError, match="host_forbidden"):
        validate_redirect(
            "https://allowed.example/start",
            "https://blocked.example/target",
            {"allowed.example"},
        )

