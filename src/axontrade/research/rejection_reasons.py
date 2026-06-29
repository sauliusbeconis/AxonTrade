"""Canonical rejection-reason catalog for signal-log rows."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_REJECTION_REASON_CATALOG = "config/research/rejection_reason_codes.yaml"

REJECTION_REASON_CATALOG_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "reason_code_order",
    "reason_codes",
    "logging_fields",
)

REJECTION_REASON_DETAIL_REQUIRED_FIELDS = (
    "category",
    "applies_to",
    "description",
    "logging_notes",
)

ALLOWED_REJECTION_REASON_CATEGORIES = frozenset(
    {
        "not_rejected",
        "setup",
        "session",
        "data_context",
        "risk",
        "calendar",
        "pacing",
        "ambiguity",
        "order_flow",
        "system",
        "fallback",
    },
)

_REASON_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class RejectionReasonCatalogError(ValueError):
    """Raised when the rejection-reason catalog is invalid."""


def load_rejection_reason_catalog(
    path: str | Path = DEFAULT_REJECTION_REASON_CATALOG,
) -> dict[str, Any]:
    """Load and validate the canonical rejection-reason catalog."""

    catalog = load_yaml(path)
    validate_rejection_reason_catalog(catalog)
    return catalog


def validate_rejection_reason_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Validate internal consistency of the rejection-reason catalog."""

    try:
        require_fields(
            catalog,
            REJECTION_REASON_CATALOG_REQUIRED_FIELDS,
            context="rejection reason catalog",
        )
    except ConfigError as exc:
        raise RejectionReasonCatalogError(str(exc)) from exc

    code_order = _require_string_list(catalog["reason_code_order"], "reason_code_order")
    if len(code_order) != len(set(code_order)):
        raise RejectionReasonCatalogError("reason_code_order contains duplicate codes")
    for code in code_order:
        _validate_reason_code(code)

    reason_codes = catalog["reason_codes"]
    if not isinstance(reason_codes, dict):
        raise RejectionReasonCatalogError("reason_codes must be a mapping")
    if set(reason_codes) != set(code_order):
        missing = sorted(set(code_order) - set(reason_codes))
        extra = sorted(set(reason_codes) - set(code_order))
        message_parts = []
        if missing:
            message_parts.append("missing details for: " + ", ".join(missing))
        if extra:
            message_parts.append("extra details for: " + ", ".join(extra))
        raise RejectionReasonCatalogError(
            "reason_codes must match reason_code_order; " + "; ".join(message_parts),
        )

    for code in code_order:
        detail = reason_codes[code]
        if not isinstance(detail, dict):
            raise RejectionReasonCatalogError(f"reason_codes.{code} must be a mapping")
        try:
            require_fields(
                detail,
                REJECTION_REASON_DETAIL_REQUIRED_FIELDS,
                context=f"reason_codes.{code}",
            )
        except ConfigError as exc:
            raise RejectionReasonCatalogError(str(exc)) from exc
        category = str(detail["category"])
        if category not in ALLOWED_REJECTION_REASON_CATEGORIES:
            raise RejectionReasonCatalogError(
                f"Invalid category for {code}: {category}",
            )
        applies_to = _require_string_list(detail["applies_to"], f"reason_codes.{code}.applies_to")
        if not applies_to:
            raise RejectionReasonCatalogError(f"reason_codes.{code}.applies_to cannot be empty")
        if not str(detail["description"]).strip():
            raise RejectionReasonCatalogError(f"reason_codes.{code}.description cannot be blank")
        if not str(detail["logging_notes"]).strip():
            raise RejectionReasonCatalogError(f"reason_codes.{code}.logging_notes cannot be blank")

    logging_fields = catalog["logging_fields"]
    if not isinstance(logging_fields, dict):
        raise RejectionReasonCatalogError("logging_fields must be a mapping")
    for field_group, field_names in logging_fields.items():
        _validate_reason_code(str(field_group), context="logging_fields key")
        _require_string_list(field_names, f"logging_fields.{field_group}")

    if "not_applicable" not in code_order:
        raise RejectionReasonCatalogError("reason_code_order must include not_applicable")
    return catalog


def rejection_reason_codes(catalog: dict[str, Any] | None = None) -> list[str]:
    """Return canonical rejection reason codes in schema order."""

    loaded_catalog = load_rejection_reason_catalog() if catalog is None else catalog
    validate_rejection_reason_catalog(loaded_catalog)
    return list(loaded_catalog["reason_code_order"])


def rejection_reason_logging_fields(
    catalog: dict[str, Any] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Return rejected-row logging field groups from the catalog."""

    loaded_catalog = load_rejection_reason_catalog() if catalog is None else catalog
    validate_rejection_reason_catalog(loaded_catalog)
    return {
        str(group_name): tuple(field_names)
        for group_name, field_names in loaded_catalog["logging_fields"].items()
    }


def _validate_reason_code(value: str, *, context: str = "reason code") -> None:
    if _REASON_CODE_PATTERN.fullmatch(value) is None:
        raise RejectionReasonCatalogError(
            f"Invalid {context}: {value}. Use lowercase snake_case.",
        )


def _require_string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RejectionReasonCatalogError(f"{context} must be a list of strings")
    return value
