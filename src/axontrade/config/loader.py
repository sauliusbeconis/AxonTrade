"""YAML configuration loading with explicit required-field validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


class ConfigError(ValueError):
    """Raised when a configuration file is missing or invalid."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping from an absolute path or repo-relative path."""

    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path

    if not config_path.exists():
        raise ConfigError(f"Configuration file does not exist: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ConfigError(f"Configuration must be a YAML mapping: {config_path}")

    return data


def require_fields(
    data: dict[str, Any],
    required_fields: Iterable[str],
    *,
    context: str = "configuration",
) -> dict[str, Any]:
    """Validate that all dotted-path fields exist in a mapping."""

    missing = [field for field in required_fields if not _has_dotted_path(data, field)]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Missing required fields in {context}: {joined}")
    return data


def _has_dotted_path(data: dict[str, Any], dotted_path: str) -> bool:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True
