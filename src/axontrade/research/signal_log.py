"""Signal-log schema validation for research and replay CSV rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_SIGNAL_LOG_SCHEMA = "config/research/signal_log_schema.yaml"


class SignalLogError(ValueError):
    """Raised when a signal-log schema or row is invalid."""


SCHEMA_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "csv.header",
    "event_types",
    "directions",
    "actions",
    "trade_modes",
    "rejection_reasons",
    "common_required_fields",
    "event_type_required_fields",
    "field_types",
    "allowed_values",
)


def load_signal_log_schema(path: str = DEFAULT_SIGNAL_LOG_SCHEMA) -> dict[str, Any]:
    """Load and validate the signal-log schema."""

    schema = load_yaml(path)
    validate_signal_log_schema(schema)
    return schema


def validate_signal_log_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Validate internal consistency of the signal-log schema."""

    try:
        require_fields(schema, SCHEMA_REQUIRED_FIELDS, context="signal log schema")
    except ConfigError as exc:
        raise SignalLogError(str(exc)) from exc

    header = _require_string_list(schema["csv"]["header"], "csv.header")
    common_required = _require_string_list(
        schema["common_required_fields"],
        "common_required_fields",
    )
    event_types = _require_string_list(schema["event_types"], "event_types")

    _ensure_subset(common_required, header, "common_required_fields", "csv.header")

    event_required = schema["event_type_required_fields"]
    if not isinstance(event_required, dict):
        raise SignalLogError("event_type_required_fields must be a mapping")

    for event_type in event_types:
        if event_type not in event_required:
            raise SignalLogError(
                f"event_type_required_fields missing event type: {event_type}",
            )
        fields = _require_string_list(
            event_required[event_type],
            f"event_type_required_fields.{event_type}",
        )
        _ensure_subset(fields, header, f"event_type_required_fields.{event_type}", "csv.header")

    field_types = schema["field_types"]
    if not isinstance(field_types, dict):
        raise SignalLogError("field_types must be a mapping")
    _ensure_subset(field_types.keys(), header, "field_types", "csv.header")

    for field_name, field_type in field_types.items():
        if field_type not in {"integer", "number", "string"}:
            raise SignalLogError(f"Unsupported field type for {field_name}: {field_type}")

    allowed_values = schema["allowed_values"]
    if not isinstance(allowed_values, dict):
        raise SignalLogError("allowed_values must be a mapping")

    for field_name, source_name in allowed_values.items():
        if field_name not in header:
            raise SignalLogError(f"allowed_values references unknown field: {field_name}")
        if source_name not in schema:
            raise SignalLogError(
                f"allowed_values.{field_name} references unknown list: {source_name}",
            )
        _require_string_list(schema[source_name], source_name)

    return schema


def validate_signal_log_row(
    row: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one signal-log row.

    Values may be native Python objects or strings loaded from CSV. Optional
    fields may be blank, but required fields must be present and nonblank.
    """

    if schema is None:
        schema = load_signal_log_schema()
    else:
        validate_signal_log_schema(schema)

    if not isinstance(row, dict):
        raise SignalLogError("signal log row must be a mapping")

    event_type = row.get("event_type")
    if _is_blank(event_type):
        raise SignalLogError("Missing required field in signal log row: event_type")

    event_type_text = str(event_type)
    if event_type_text not in schema["event_types"]:
        raise SignalLogError(f"Invalid event_type: {event_type_text}")

    required_fields = list(schema["common_required_fields"])
    required_fields.extend(schema["event_type_required_fields"][event_type_text])
    _require_nonblank_fields(row, required_fields)

    allowed_values = schema["allowed_values"]
    for field_name, source_name in allowed_values.items():
        value = row.get(field_name)
        if _is_blank(value):
            continue
        allowed = set(schema[source_name])
        if str(value) not in allowed:
            raise SignalLogError(
                f"Invalid {field_name}: {value}. Expected one of: {', '.join(sorted(allowed))}",
            )

    for field_name, field_type in schema["field_types"].items():
        value = row.get(field_name)
        if _is_blank(value):
            continue
        _validate_field_type(field_name, value, field_type)

    return row


def validate_signal_log_rows(
    rows: Iterable[dict[str, Any]],
    schema: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate multiple signal-log rows and return them as a list."""

    loaded_schema = load_signal_log_schema() if schema is None else schema
    return [validate_signal_log_row(row, loaded_schema) for row in rows]


def load_signal_log_rows_csv(
    path: str | Path,
    schema: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Load signal-log CSV rows and validate the contract."""

    loaded_schema = load_signal_log_schema() if schema is None else schema
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        expected_header = list(loaded_schema["csv"]["header"])
        if header != expected_header:
            raise SignalLogError(
                "Signal log CSV header mismatch. "
                f"Expected {expected_header}, got {header}",
            )
        return validate_signal_log_rows(list(reader), loaded_schema)


def _require_nonblank_fields(row: dict[str, Any], field_names: Iterable[str]) -> None:
    missing = [field_name for field_name in field_names if _is_blank(row.get(field_name))]
    if missing:
        raise SignalLogError(
            "Missing required fields in signal log row: " + ", ".join(missing),
        )


def _validate_field_type(field_name: str, value: Any, field_type: str) -> None:
    try:
        if field_type == "integer":
            int(str(value))
        elif field_type == "number":
            float(str(value))
        elif field_type == "string":
            str(value)
        else:
            raise SignalLogError(f"Unsupported field type for {field_name}: {field_type}")
    except ValueError as exc:
        raise SignalLogError(
            f"Invalid {field_name}: expected {field_type}, got {value!r}",
        ) from exc


def _require_string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SignalLogError(f"{context} must be a list of strings")
    return value


def _ensure_subset(
    values: Iterable[str],
    allowed_values: Iterable[str],
    values_context: str,
    allowed_context: str,
) -> None:
    allowed = set(allowed_values)
    unknown = [value for value in values if value not in allowed]
    if unknown:
        raise SignalLogError(
            f"{values_context} contains values not present in {allowed_context}: "
            + ", ".join(unknown),
        )


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
