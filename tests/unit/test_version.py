from __future__ import annotations

from pathlib import Path
import sys

if sys.version_info >= (3, 11):
    import tomllib as toml_loader
else:  # pragma: no cover - Python < 3.11 fallback
    import tomli as toml_loader

from business_bridge.api.runtime import APP_VERSION


def test_runtime_version_matches_pyproject() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    pyproject = toml_loader.loads(pyproject_path.read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == APP_VERSION
