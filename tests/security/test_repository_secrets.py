import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNED_SUFFIXES = {".py", ".json", ".md", ".toml", ".yml", ".yaml"}
SECRET_PATTERNS = (
    re.compile(r"ya29\.[A-Za-z0-9._~-]{16,}"),
    re.compile(r"aas_et/[A-Za-z0-9._~+/-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def test_repository_contains_no_token_or_private_key_patterns() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if any(part in {".audit_upstream", ".audit_venv", ".git"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_config_entry_code_never_persists_passphrase() -> None:
    source = (ROOT / "custom_components/private_find_hub/config_flow.py").read_text(
        encoding="utf-8"
    )
    create_entry_blocks = re.findall(r"async_create_entry\((.*?)\n\s*\)", source, re.DOTALL)
    assert create_entry_blocks
    assert all("CONF_PASSPHRASE:" not in block for block in create_entry_blocks)

