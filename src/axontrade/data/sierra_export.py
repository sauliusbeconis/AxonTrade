"""Normalize Sierra Chart bar and study exports for research baselines."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_SIERRA_EXPORT_CONFIG = "config/research/sierra_bar_export.yaml"
DEFAULT_OPENING_RANGE_START_TIME = "09:30:00"
DEFAULT_OPENING_RANGE_END_TIME = "09:59:59"
_COMPUTED_OPENING_RANGE_FIELDS = {"opening_range_high", "opening_range_low"}
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class SierraExportError(ValueError):
    """Raised when a Sierra export cannot be normalized."""


@dataclass(frozen=True)
class SierraExportFieldStatus:
    """Column readiness status for one normalized export field."""

    field_name: str
    status: str
    matched_header: str
    required: bool


SIERRA_EXPORT_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "normalized_fields",
    "defaults.chart_number",
    "defaults.session_phase",
    "required_cli_values",
    "column_aliases",
)


def load_sierra_export_config(
    path: str = DEFAULT_SIERRA_EXPORT_CONFIG,
) -> dict[str, Any]:
    """Load and validate the Sierra export normalization config."""

    config = load_yaml(path)
    validate_sierra_export_config(config)
    return config


def validate_sierra_export_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the Sierra export normalization config."""

    try:
        require_fields(config, SIERRA_EXPORT_REQUIRED_FIELDS, context="Sierra export config")
    except ConfigError as exc:
        raise SierraExportError(str(exc)) from exc

    if not isinstance(config["normalized_fields"], list):
        raise SierraExportError("normalized_fields must be a list")
    if "optional_fields" in config and not isinstance(config["optional_fields"], list):
        raise SierraExportError("optional_fields must be a list")
    if not isinstance(config["required_cli_values"], list):
        raise SierraExportError("required_cli_values must be a list")
    if not isinstance(config["column_aliases"], dict):
        raise SierraExportError("column_aliases must be a mapping")

    optional_fields = set(config.get("optional_fields", []))
    for field_name in config["normalized_fields"]:
        if (
            field_name not in config["column_aliases"]
            and field_name not in config["defaults"]
            and field_name not in optional_fields
        ):
            raise SierraExportError(
                f"normalized field has no aliases or default: {field_name}",
            )

    return config


def load_sierra_bar_study_rows(path: str | Path) -> list[dict[str, str]]:
    """Load Sierra Chart's exported bar/study text file.

    Sierra exports may be comma-separated or tab-separated depending on settings
    and version, so this uses a small delimiter sniff with a stable fallback.
    """

    export_path = Path(path)
    text = export_path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in sample else csv.excel

    reader = csv.reader(text.splitlines(), dialect=dialect)
    try:
        headers = next(reader)
    except StopIteration:
        return []

    unique_headers = _make_unique_headers(headers)
    rows: list[dict[str, str]] = []
    for values in reader:
        if not values or all(value.strip() == "" for value in values):
            continue
        row = {
            header: values[index].strip() if index < len(values) else ""
            for index, header in enumerate(unique_headers)
        }
        rows.append(row)

    return rows


def inspect_sierra_bar_study_file(
    path: str | Path,
    *,
    config: dict[str, Any] | None = None,
    compute_opening_range: bool = True,
) -> dict[str, Any]:
    """Inspect an export file and report which normalized fields are available."""

    rows = load_sierra_bar_study_rows(path)
    export_config = load_sierra_export_config() if config is None else config
    validate_sierra_export_config(export_config)
    headers = list(rows[0].keys()) if rows else []
    field_statuses = inspect_sierra_bar_study_headers(
        headers,
        config=export_config,
        compute_opening_range=compute_opening_range,
    )
    missing_required = [
        status.field_name
        for status in field_statuses
        if status.required and status.status == "missing"
    ]
    missing_optional = [
        status.field_name
        for status in field_statuses
        if not status.required and status.status == "missing"
    ]
    return {
        "row_count": len(rows),
        "headers": headers,
        "fields": field_statuses,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "ready": len(rows) > 0 and not missing_required,
    }


def inspect_sierra_bar_study_headers(
    headers: Iterable[str],
    *,
    config: dict[str, Any] | None = None,
    compute_opening_range: bool = True,
) -> list[SierraExportFieldStatus]:
    """Inspect export headers without raising on missing normalized fields."""

    export_config = load_sierra_export_config() if config is None else config
    validate_sierra_export_config(export_config)
    header_list = [header for header in headers if header is not None]
    normalized_to_original = {_normalize_header(header): header for header in header_list}
    computed_fields = _COMPUTED_OPENING_RANGE_FIELDS if compute_opening_range else set()
    optional_fields = set(export_config.get("optional_fields", []))
    defaulted_fields = {"symbol", "chart_number", "bar_index", "session_phase"}

    statuses: list[SierraExportFieldStatus] = []
    for field_name in export_config["normalized_fields"]:
        if field_name in computed_fields:
            statuses.append(
                SierraExportFieldStatus(
                    field_name=field_name,
                    status="computed",
                    matched_header="",
                    required=False,
                ),
            )
            continue

        if (
            field_name == "timestamp"
            and "date" in normalized_to_original
            and "time" in normalized_to_original
        ):
            statuses.append(
                SierraExportFieldStatus(
                    field_name=field_name,
                    status="matched",
                    matched_header="Date + Time",
                    required=True,
                ),
            )
            continue

        aliases = export_config["column_aliases"].get(field_name, [])
        matched_header = _match_header(field_name, aliases, header_list, normalized_to_original)
        if matched_header is not None:
            statuses.append(
                SierraExportFieldStatus(
                    field_name=field_name,
                    status="matched",
                    matched_header=matched_header,
                    required=field_name not in optional_fields,
                ),
            )
            continue

        if field_name in defaulted_fields:
            statuses.append(
                SierraExportFieldStatus(
                    field_name=field_name,
                    status="defaulted",
                    matched_header="",
                    required=False,
                ),
            )
            continue

        statuses.append(
            SierraExportFieldStatus(
                field_name=field_name,
                status="missing",
                matched_header="",
                required=field_name not in optional_fields,
            ),
        )

    return statuses


def normalize_sierra_bar_study_rows(
    rows: Iterable[dict[str, Any]],
    *,
    symbol: str,
    chart_number: int | None = None,
    session_phase: str | None = None,
    config: dict[str, Any] | None = None,
    compute_opening_range: bool = False,
    opening_range_start_time: str = DEFAULT_OPENING_RANGE_START_TIME,
    opening_range_end_time: str = DEFAULT_OPENING_RANGE_END_TIME,
) -> list[dict[str, Any]]:
    """Normalize Sierra export rows to the price-only baseline row contract."""

    if not symbol:
        raise SierraExportError("symbol is required")

    export_config = load_sierra_export_config() if config is None else config
    validate_sierra_export_config(export_config)

    normalized_rows: list[dict[str, Any]] = []
    header_mapping: dict[str, str] | None = None
    computed_fields = _COMPUTED_OPENING_RANGE_FIELDS if compute_opening_range else set()

    for generated_index, row in enumerate(rows):
        if header_mapping is None:
            header_mapping = _build_header_mapping(
                row.keys(),
                export_config,
                computed_fields=computed_fields,
            )

        normalized = {}
        for field_name in export_config["normalized_fields"]:
            if field_name in computed_fields:
                continue
            normalized[field_name] = _resolve_field_value(
                field_name,
                row,
                header_mapping,
                export_config,
                symbol=symbol,
                chart_number=chart_number,
                session_phase=session_phase,
                generated_index=generated_index,
            )
        normalized_rows.append(normalized)

    if compute_opening_range:
        return _with_computed_opening_range_levels(
            normalized_rows,
            start_time_value=opening_range_start_time,
            end_time_value=opening_range_end_time,
        )

    return normalized_rows


def normalize_sierra_bar_study_file(
    path: str | Path,
    *,
    symbol: str,
    chart_number: int | None = None,
    session_phase: str | None = None,
    config: dict[str, Any] | None = None,
    compute_opening_range: bool = True,
    opening_range_start_time: str = DEFAULT_OPENING_RANGE_START_TIME,
    opening_range_end_time: str = DEFAULT_OPENING_RANGE_END_TIME,
) -> list[dict[str, Any]]:
    """Load and normalize one Sierra export file."""

    rows = load_sierra_bar_study_rows(path)
    return normalize_sierra_bar_study_rows(
        rows,
        symbol=symbol,
        chart_number=chart_number,
        session_phase=session_phase,
        config=config,
        compute_opening_range=compute_opening_range,
        opening_range_start_time=opening_range_start_time,
        opening_range_end_time=opening_range_end_time,
    )


def _build_header_mapping(
    headers: Iterable[str],
    config: dict[str, Any],
    *,
    computed_fields: set[str] | None = None,
) -> dict[str, str]:
    header_list = [header for header in headers if header is not None]
    normalized_to_original = {_normalize_header(header): header for header in header_list}
    mapping: dict[str, str] = {}
    computed_fields = computed_fields or set()
    optional_fields = set(config.get("optional_fields", []))

    for field_name, aliases in config["column_aliases"].items():
        if field_name in computed_fields:
            continue
        if field_name == "timestamp" and "date" in normalized_to_original and "time" in normalized_to_original:
            mapping[field_name] = "__date_time__"
            continue

        if field_name in {"symbol", "chart_number", "bar_index", "session_phase"}:
            optional = True
        else:
            optional = field_name in optional_fields

        matched_header = _match_header(field_name, aliases, header_list, normalized_to_original)
        if matched_header is None:
            if optional:
                continue
            raise SierraExportError(
                f"Missing Sierra export column for {field_name}. "
                f"Known headers: {', '.join(header_list)}",
            )
        mapping[field_name] = matched_header

    return mapping


def _match_header(
    field_name: str,
    aliases: list[str],
    headers: list[str],
    normalized_to_original: dict[str, str],
) -> str | None:
    for alias in aliases:
        normalized_alias = _normalize_header(alias)
        if normalized_alias in normalized_to_original:
            return normalized_to_original[normalized_alias]

    if field_name in {"vwap", "opening_range_high", "opening_range_low"}:
        for alias in aliases:
            normalized_alias = _normalize_header(alias)
            for header in headers:
                normalized_header = _normalize_header(header)
                if normalized_alias and normalized_alias in normalized_header:
                    return header

    if field_name == "opening_range_high":
        return _last_duplicate_study_header(headers, "High")
    if field_name == "opening_range_low":
        return _last_duplicate_study_header(headers, "Low")

    return None


def _resolve_field_value(
    field_name: str,
    row: dict[str, Any],
    header_mapping: dict[str, str],
    config: dict[str, Any],
    *,
    symbol: str,
    chart_number: int | None,
    session_phase: str | None,
    generated_index: int,
) -> Any:
    optional_fields = set(config.get("optional_fields", []))
    if field_name in optional_fields and field_name not in header_mapping:
        return ""

    if field_name == "symbol":
        return _value_or_default(row, header_mapping, field_name, symbol)
    if field_name == "chart_number":
        default_chart_number = chart_number or int(config["defaults"]["chart_number"])
        return _value_or_default(row, header_mapping, field_name, default_chart_number)
    if field_name == "bar_index":
        return _value_or_default(row, header_mapping, field_name, generated_index)
    if field_name == "session_phase":
        default_session_phase = session_phase or str(config["defaults"]["session_phase"])
        return _value_or_default(row, header_mapping, field_name, default_session_phase)
    if field_name == "timestamp" and header_mapping.get(field_name) == "__date_time__":
        date_value = row.get("Date", "")
        time_value = row.get("Time", "")
        timestamp = f"{date_value} {time_value}".strip()
        if timestamp == "":
            raise SierraExportError("Blank Sierra export value for timestamp")
        return timestamp

    source_header = header_mapping[field_name]
    value = row.get(source_header)
    if value is None or str(value).strip() == "":
        if field_name in optional_fields:
            return ""
        raise SierraExportError(f"Blank Sierra export value for {field_name}")
    return value


def _value_or_default(
    row: dict[str, Any],
    header_mapping: dict[str, str],
    field_name: str,
    default_value: Any,
) -> Any:
    source_header = header_mapping.get(field_name)
    if source_header is None:
        return default_value

    value = row.get(source_header)
    if value is None or str(value).strip() == "":
        return default_value
    return value


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _with_computed_opening_range_levels(
    rows: list[dict[str, Any]],
    *,
    start_time_value: str,
    end_time_value: str,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    start_time = _parse_time(start_time_value, "opening_range_start_time")
    end_time = _parse_time(end_time_value, "opening_range_end_time")
    if start_time > end_time:
        raise SierraExportError("opening_range_start_time must be before opening_range_end_time")

    parsed_timestamps: list[datetime] = []
    opening_ranges: dict[tuple[str, str], tuple[float, float]] = {}
    for row in rows:
        timestamp = _parse_timestamp(str(row["timestamp"]))
        parsed_timestamps.append(timestamp)

        if start_time <= timestamp.time() <= end_time:
            key = _opening_range_key(row, timestamp)
            bar_high = _parse_float(row["high"], "high")
            bar_low = _parse_float(row["low"], "low")
            if key in opening_ranges:
                current_high, current_low = opening_ranges[key]
                opening_ranges[key] = (max(current_high, bar_high), min(current_low, bar_low))
            else:
                opening_ranges[key] = (bar_high, bar_low)

    enriched_rows: list[dict[str, Any]] = []
    for row, timestamp in zip(rows, parsed_timestamps, strict=True):
        key = _opening_range_key(row, timestamp)
        if key not in opening_ranges:
            raise SierraExportError(
                "No bars found inside opening range "
                f"{start_time_value}-{end_time_value} for {key[0]} on {key[1]}",
            )
        opening_range_high, opening_range_low = opening_ranges[key]
        enriched_row = dict(row)
        enriched_row["opening_range_high"] = _format_price(opening_range_high)
        enriched_row["opening_range_low"] = _format_price(opening_range_low)
        enriched_rows.append(enriched_row)

    return enriched_rows


def _opening_range_key(row: dict[str, Any], timestamp: datetime) -> tuple[str, str]:
    return str(row["symbol"]), timestamp.date().isoformat()


def _parse_time(value: str, field_name: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), "%H:%M:%S").time()
    except ValueError as exc:
        raise SierraExportError(f"Invalid {field_name}: {value!r}") from exc


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = value.strip()
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SierraExportError(f"Invalid timestamp: {value!r}")


def _parse_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SierraExportError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _format_price(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _make_unique_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique_headers: list[str] = []
    for header in headers:
        clean_header = header.strip()
        seen[clean_header] = seen.get(clean_header, 0) + 1
        if seen[clean_header] == 1:
            unique_headers.append(clean_header)
        else:
            unique_headers.append(f"{clean_header}__{seen[clean_header]}")
    return unique_headers


def _last_duplicate_study_header(headers: list[str], base_name: str) -> str | None:
    candidates = [
        header
        for header in headers
        if header.startswith(f"{base_name}__")
    ]
    if candidates:
        return candidates[-1]
    return None
