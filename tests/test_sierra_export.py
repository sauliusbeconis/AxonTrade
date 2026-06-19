from __future__ import annotations

import csv

import pytest

from axontrade.data import (
    SierraExportError,
    load_sierra_bar_study_rows,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
    normalize_sierra_bar_study_rows,
    validate_sierra_export_config,
)
from axontrade.research import evaluate_price_only_vwap_reclaim


def _sierra_export_rows() -> list[dict[str, str]]:
    return [
        {
            "Date Time": "2026-06-19 09:30:00",
            "Open": "99.0",
            "High": "100.0",
            "Low": "98.0",
            "Last": "99.0",
            "Volume Weighted Average Price - VWAP": "100.0",
            "Opening Range High": "100.0",
            "Opening Range Low": "90.0",
        },
        {
            "Date Time": "2026-06-19 09:31:00",
            "Open": "100.5",
            "High": "102.0",
            "Low": "99.5",
            "Last": "101.0",
            "Volume Weighted Average Price - VWAP": "100.0",
            "Opening Range High": "100.0",
            "Opening Range Low": "90.0",
        },
    ]


def test_loads_sierra_export_config() -> None:
    config = load_sierra_export_config()

    assert config["profile_id"] == "sierra_bar_study_export_v1"
    assert "vwap" in config["column_aliases"]


def test_sierra_export_config_is_valid() -> None:
    validate_sierra_export_config(load_sierra_export_config())


def test_normalizes_sierra_export_rows_for_baseline() -> None:
    rows = normalize_sierra_bar_study_rows(_sierra_export_rows(), symbol="ESU26-CME")

    assert rows[0]["symbol"] == "ESU26-CME"
    assert rows[0]["chart_number"] == 1
    assert rows[0]["bar_index"] == 0
    assert rows[0]["close"] == "99.0"
    assert rows[0]["vwap"] == "100.0"
    assert rows[0]["session_phase"] == "rth"


def test_normalized_sierra_rows_feed_price_only_baseline() -> None:
    rows = normalize_sierra_bar_study_rows(_sierra_export_rows(), symbol="ESU26-CME")

    signal_rows = evaluate_price_only_vwap_reclaim(rows)

    assert signal_rows[0]["event_type"] == "rejected_signal"
    assert signal_rows[1]["event_type"] == "candidate_signal"
    assert signal_rows[1]["direction"] == "long"


def test_loads_comma_export_file(tmp_path) -> None:
    export_path = tmp_path / "sierra-export.csv"
    rows = _sierra_export_rows()
    with export_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    loaded_rows = load_sierra_bar_study_rows(export_path)
    normalized_rows = normalize_sierra_bar_study_file(export_path, symbol="ESU26-CME")

    assert len(loaded_rows) == 2
    assert normalized_rows[1]["bar_index"] == 1


def test_loads_tab_export_file(tmp_path) -> None:
    export_path = tmp_path / "sierra-export.txt"
    export_path.write_text(
        "Date Time\tOpen\tHigh\tLow\tLast\tVWAP\tOR High\tOR Low\n"
        "2026-06-19 09:30:00\t99\t100\t98\t99\t100\t100\t90\n",
        encoding="utf-8",
    )

    normalized_rows = normalize_sierra_bar_study_file(export_path, symbol="ESU26-CME")

    assert normalized_rows[0]["timestamp"] == "2026-06-19 09:30:00"
    assert normalized_rows[0]["opening_range_high"] == "100"


def test_normalizes_actual_sierra_duplicate_headers(tmp_path) -> None:
    rows = load_sierra_bar_study_rows(
        _write_export_text(
            tmp_path,
            "Date, Time, Open, High, Low, Last, Volume, VWAP, High, Low, Open, High, Low, Close, High, Low\n"
            "2026-6-10, 09:30:00.000000, 7396.75, 7399.00, 7395.25, 7398.25, 22, 7398.25, 7466.25, 7365.50, 7396.75, 7466.25, 7365.50, 7382.50, 7466.25, 7365.50\n"
        )
    )

    normalized_rows = normalize_sierra_bar_study_rows(rows, symbol="ESU26-CME")

    assert normalized_rows[0]["timestamp"] == "2026-6-10 09:30:00.000000"
    assert normalized_rows[0]["open"] == "7396.75"
    assert normalized_rows[0]["high"] == "7399.00"
    assert normalized_rows[0]["low"] == "7395.25"
    assert normalized_rows[0]["close"] == "7398.25"
    assert normalized_rows[0]["vwap"] == "7398.25"
    assert normalized_rows[0]["opening_range_high"] == "7466.25"
    assert normalized_rows[0]["opening_range_low"] == "7365.50"


def test_rejects_missing_required_export_column() -> None:
    rows = _sierra_export_rows()
    del rows[0]["Volume Weighted Average Price - VWAP"]
    del rows[1]["Volume Weighted Average Price - VWAP"]

    with pytest.raises(SierraExportError, match="vwap"):
        normalize_sierra_bar_study_rows(rows, symbol="ESU26-CME")


def _write_export_text(tmp_path, text: str) -> str:
    export_path = tmp_path / "actual-sierra-export.txt"
    export_path.write_text(text, encoding="utf-8")
    return str(export_path)
