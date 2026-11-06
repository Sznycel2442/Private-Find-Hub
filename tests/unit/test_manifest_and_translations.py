import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components/private_find_hub"


def test_manifest_has_pinned_minimal_runtime_dependency() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "private_find_hub"
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == ["argon2-cffi==25.1.0"]
    assert manifest["single_config_entry"] is True


def test_polish_and_english_translations_are_valid_json() -> None:
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    for language in ("en", "pl"):
        translated = json.loads(
            (INTEGRATION / "translations" / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        assert set(translated) >= {"config", "entity"}
    assert set(strings) >= {"config", "entity", "options"}
