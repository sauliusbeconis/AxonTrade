from __future__ import annotations

import csv

import pytest

from axontrade.data import (
    SierraExportError,
    inspect_sierra_bar_study_file,
    inspect_sierra_bar_study_headers,
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
            "Date Time": "2026-06-19 10:00:00",
            "Open": "99.0",
            "High": "100.0",
            "Low": "98.0",
            "Last": "99.0",
            "Volume Weighted Average Price - VWAP": "100.0",
            "Opening Range High": "100.0",
            "Opening Range Low": "90.0",
        },
        {
            "Date Time": "2026-06-19 10:01:00",
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


def test_orderflow_export_config_is_valid() -> None:
    config = load_sierra_export_config("config/research/sierra_orderflow_bar_export.yaml")

    validate_sierra_export_config(config)
    assert "bid_volume" in config["normalized_fields"]
    assert "number_of_trades" in config["optional_fields"]
    assert "delta" in config["optional_fields"]


def test_delta_impulse_export_config_is_valid() -> None:
    config = load_sierra_export_config("config/research/sierra_delta_impulse_bar_export.yaml")

    validate_sierra_export_config(config)
    assert "bid_volume" in config["normalized_fields"]
    assert "ask_volume" in config["normalized_fields"]
    assert "vwap" not in config["normalized_fields"]
    assert "delta" in config["optional_fields"]


def test_volume_at_price_export_config_is_valid() -> None:
    config = load_sierra_export_config("config/research/sierra_volume_at_price_export.yaml")

    validate_sierra_export_config(config)
    assert "price" in config["normalized_fields"]
    assert "number_of_trades" in config["optional_fields"]


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
    normalized_rows = normalize_sierra_bar_study_file(
        export_path,
        symbol="ESU26-CME",
        compute_opening_range=False,
    )

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


def test_computes_opening_range_from_exported_bars(tmp_path) -> None:
    export_path = tmp_path / "sierra-export-no-or-study.csv"
    export_path.write_text(
        "Date,Time,Open,High,Low,Last,VWAP\n"
        "2026-6-19,09:30:00.000000,100,101,98,99,100\n"
        "2026-6-19,09:59:00.000000,99,105,97,99,100\n"
        "2026-6-19,10:00:00.000000,105,106.5,104,106,100\n",
        encoding="utf-8",
    )

    normalized_rows = normalize_sierra_bar_study_file(export_path, symbol="ESU26-CME")
    signal_rows = evaluate_price_only_vwap_reclaim(normalized_rows)

    assert normalized_rows[2]["opening_range_high"] == "105"
    assert normalized_rows[2]["opening_range_low"] == "97"
    assert signal_rows[0]["rejection_reason"] == "insufficient_context"
    assert signal_rows[1]["rejection_reason"] == "insufficient_context"
    assert signal_rows[2]["event_type"] == "candidate_signal"
    assert signal_rows[2]["direction"] == "long"


def test_normalizes_optional_orderflow_fields() -> None:
    config = load_sierra_export_config("config/research/sierra_orderflow_bar_export.yaml")
    rows = normalize_sierra_bar_study_rows(
        [
            {
                "Date Time": "2026-06-19 10:30:00",
                "Open": "100",
                "High": "101",
                "Low": "99",
                "Last": "100.5",
                "VWAP": "100",
                "OR High": "101",
                "OR Low": "99",
                "Bid Volume": "80",
                "Ask Volume": "120",
                "# of Trades": "10",
            },
        ],
        symbol="ESU26-CME",
        config=config,
    )

    assert rows[0]["bid_volume"] == "80"
    assert rows[0]["ask_volume"] == "120"
    assert rows[0]["number_of_trades"] == "10"
    assert rows[0]["delta"] == ""
    assert rows[0]["volume"] == ""


def test_inspects_orderflow_export_headers() -> None:
    config = load_sierra_export_config("config/research/sierra_orderflow_bar_export.yaml")
    statuses = inspect_sierra_bar_study_headers(
        [
            "Date Time",
            "Open",
            "High",
            "Low",
            "Last",
            "VWAP",
            "Bid Volume",
            "Ask Volume",
        ],
        config=config,
    )
    by_field = {status.field_name: status for status in statuses}

    assert by_field["timestamp"].status == "matched"
    assert by_field["opening_range_high"].status == "computed"
    assert by_field["bid_volume"].matched_header == "Bid Volume"
    assert by_field["ask_volume"].matched_header == "Ask Volume"
    assert by_field["delta"].status == "missing"
    assert by_field["delta"].required is False


def test_inspects_volume_at_price_export_headers() -> None:
    config = load_sierra_export_config("config/research/sierra_volume_at_price_export.yaml")
    statuses = inspect_sierra_bar_study_headers(
        [
            "Date Time",
            "Open",
            "High",
            "Low",
            "Last",
            "Price",
            "Bid Volume",
            "Ask Volume",
            "Volume",
            "Trades",
        ],
        config=config,
        compute_opening_range=False,
    )
    by_field = {status.field_name: status for status in statuses}

    assert by_field["timestamp"].status == "matched"
    assert by_field["price"].matched_header == "Price"
    assert by_field["bid_volume"].matched_header == "Bid Volume"
    assert by_field["ask_volume"].matched_header == "Ask Volume"
    assert by_field["level_volume"].matched_header == "Volume"
    assert by_field["delta"].status == "missing"
    assert by_field["delta"].required is False
    assert by_field["number_of_trades"].matched_header == "Trades"


def test_normalizes_volume_at_price_export_rows() -> None:
    config = load_sierra_export_config("config/research/sierra_volume_at_price_export.yaml")
    rows = normalize_sierra_bar_study_rows(
        [
            {
                "Date Time": "2026-06-19 10:30:00",
                "Open": "100",
                "High": "101",
                "Low": "99",
                "Last": "100.5",
                "Price": "100.25",
                "Bid Volume": "80",
                "Ask Volume": "120",
                "Trades": "15",
            },
        ],
        symbol="ESU26-CME",
        config=config,
    )

    assert rows[0]["timestamp"] == "2026-06-19 10:30:00"
    assert rows[0]["price"] == "100.25"
    assert rows[0]["bid_volume"] == "80"
    assert rows[0]["ask_volume"] == "120"
    assert rows[0]["level_volume"] == ""
    assert rows[0]["delta"] == ""
    assert rows[0]["number_of_trades"] == "15"


def test_inspects_missing_required_orderflow_export_fields(tmp_path) -> None:
    export_path = tmp_path / "missing-orderflow.txt"
    export_path.write_text(
        "Date Time,Open,High,Low,Last,VWAP\n"
        "2026-06-19 10:30:00,100,101,99,100.5,100\n",
        encoding="utf-8",
    )
    config = load_sierra_export_config("config/research/sierra_orderflow_bar_export.yaml")

    inspection = inspect_sierra_bar_study_file(export_path, config=config)

    assert inspection["ready"] is False
    assert inspection["row_count"] == 1
    assert "bid_volume" in inspection["missing_required"]
    assert "ask_volume" in inspection["missing_required"]


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
