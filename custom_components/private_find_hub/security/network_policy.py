from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from urllib.parse import urlsplit

from ..api.exceptions import NetworkPolicyError

RUNTIME_ALLOWED_HOSTS: frozenset[str] = frozenset()


def validate_https_url(url: str, allowed_hosts: Iterable[str] = RUNTIME_ALLOWED_HOSTS) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError) as err:
        raise NetworkPolicyError("url_invalid") from err
    if parsed.scheme != "https" or not host:
        raise NetworkPolicyError("https_required")
    if parsed.username is not None or parsed.password is not None:
        raise NetworkPolicyError("userinfo_forbidden")
    if port not in (None, 443):
        raise NetworkPolicyError("port_forbidden")
    normalized = host.casefold().rstrip(".")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise NetworkPolicyError("ip_literal_forbidden")
    allowed = {item.casefold().rstrip(".") for item in allowed_hosts}
    if normalized not in allowed:
        raise NetworkPolicyError("host_forbidden")
    return normalized


def validate_redirect(source_url: str, target_url: str, allowed_hosts: Iterable[str]) -> None:
    validate_https_url(source_url, allowed_hosts)
    validate_https_url(target_url, allowed_hosts)
