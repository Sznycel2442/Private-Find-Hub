from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ".git",
    ".audit_upstream",
    ".audit_venv",
    ".ci_venv",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "venv",
}
SKIP_FILES = {".coverage", "coverage.xml"}
PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:[a-z]:\\" + r"users\\|/ho" + r"me/|/us" + r"ers/)[^\s/\\]+"),
    re.compile(r"gh[opsu]_[0-9A-Za-z]{20,}"),
)
FORBIDDEN_RUNTIME = ("tile.openstreetmap.org", "google.com/maps", "analytics.google.com")


def files():
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and path.name not in SKIP_FILES
            and not any(part in SKIP for part in path.parts)
        ):
            yield path


def main() -> int:
    failures: list[str] = []
    manifest = json.loads(
        (ROOT / "custom_components/private_find_hub/manifest.json").read_text("utf-8")
    )
    if manifest.get("domain") != "private_find_hub":
        failures.append("manifest_domain")
    for path in files():
        try:
            value = path.read_text("utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(pattern.search(value) for pattern in PATTERNS):
            failures.append(f"secret_pattern:{relative}")
        if relative.startswith("custom_components/") and any(
            host in value for host in FORBIDDEN_RUNTIME
        ):
            failures.append(f"forbidden_runtime_host:{relative}")
    if failures:
        print("\n".join(sorted(failures)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
