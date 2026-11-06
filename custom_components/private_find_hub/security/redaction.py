from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "**REDACTED**"
SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "cookie",
        "email",
        "fcm_token",
        "latitude",
        "longitude",
        "oauth_token",
        "owner_key",
        "password",
        "refresh_token",
        "secret",
        "shared_key",
        "token",
    }
)
EMAIL_PATTERN = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
TOKEN_PATTERN = re.compile(r"(?i)\b(?:ya29\.|aas_et/|bearer\s+)[a-z0-9._~+/-]+")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if str(key).casefold() in SENSITIVE_KEYS else redact(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(child) for child in value]
    if isinstance(value, str):
        cleaned = EMAIL_PATTERN.sub(REDACTED, value)
        return TOKEN_PATTERN.sub(REDACTED, cleaned)
    return value


def safe_exception_name(err: BaseException) -> str:
    return type(err).__name__

