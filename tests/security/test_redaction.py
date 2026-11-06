from custom_components.private_find_hub.security.redaction import (
    REDACTED,
    redact,
    safe_exception_name,
)


def test_recursive_redaction_removes_sensitive_values() -> None:
    result = redact(
        {
            "token": "ya29.secret",
            "nested": {
                "email": "owner@example.com",
                "latitude": 12.345,
                "message": "Bearer very-secret-value for owner@example.com",
            },
        }
    )
    assert result["token"] == REDACTED
    assert result["nested"]["email"] == REDACTED
    assert result["nested"]["latitude"] == REDACTED
    assert "owner@example.com" not in result["nested"]["message"]
    assert "very-secret-value" not in result["nested"]["message"]


def test_redaction_collections_and_safe_exception() -> None:
    assert redact(("plain", {"password": "secret"})) == ["plain", {"password": REDACTED}]
    assert redact(42) == 42
    assert safe_exception_name(ValueError("sensitive")) == "ValueError"
