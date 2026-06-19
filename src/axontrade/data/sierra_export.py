"""Normalize Sierra Chart bar and study exports for research baselines."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields


DEFAULT_SIERRA_EXPORT_CONFIG = "config/research/sierra_bar_export.yaml"


class SierraExportError(ValueError):
    """Raised when a Sierra export cannot be normalized."""


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
    if not isinstance(config["required_cli_values"], list):
        raise SierraExportError("required_cli_values must be a list")
    if not isinstance(config["column_aliases"], dict):
        raise SierraExportError("column_aliases must be a mapping")

    for field_name in config["normalized_fields"]:
        if field_name not in config["column_aliases"] and field_name not in config["defaults"]:
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


def normalize_sierra_bar_study_rows(
    rows: Iterable[dict[str, Any]],
    *,
    symbol: str,
    chart_number: int | None = None,
    session_phase: str | None = None,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Normalize Sierra export rows to the price-only baseline row contract."""

    if not symbol:
        raise SierraExportError("symbol is required")

    export_config = load_sierra_export_config() if config is None else config
    validate_sierra_export_config(export_config)

    normalized_rows: list[dict[str, Any]] = []
    header_mapping: dict[str, str] | None = None

    for generated_index, row in enumerate(rows):
        if header_mapping is None:
            header_mapping = _build_header_mapping(row.keys(), export_config)

        normalized = {}
        for field_name in export_config["normalized_fields"]:
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

    return normalized_rows


def normalize_sierra_bar_study_file(
    path: str | Path,
    *,
    symbol: str,
    chart_number: int | None = None,
    session_phase: str | None = None,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Load and normalize one Sierra export file."""

    rows = load_sierra_bar_study_rows(path)
    return normalize_sierra_bar_study_rows(
        rows,
        symbol=symbol,
        chart_number=chart_number,
        session_phase=session_phase,
        config=config,
    )


def _build_header_mapping(
    headers: Iterable[str],
    config: dict[str, Any],
) -> dict[str, str]:
    header_list = [header for header in headers if header is not None]
    normalized_to_original = {_normalize_header(header): header for header in header_list}
    mapping: dict[str, str] = {}

    for field_name, aliases in config["column_aliases"].items():
        if field_name == "timestamp" and "date" in normalized_to_original and "time" in normalized_to_original:
            mapping[field_name] = "__date_time__"
            continue

        if field_name in {"symbol", "chart_number", "bar_index", "session_phase"}:
            optional = True
        else:
            optional = False

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
