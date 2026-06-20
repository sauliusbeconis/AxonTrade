from __future__ import annotations

import pytest

from axontrade.config import load_yaml
from axontrade.research import (
    SignalLogError,
    load_signal_log_schema,
    validate_signal_log_row,
    validate_signal_log_schema,
)


def _candidate_row() -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_key": "ES:1:100:price_only_vwap_reclaim:long",
        "event_type": "candidate_signal",
        "generated_at": "2026-06-19 10:05:00",
        "symbol": "ESU26-CME",
        "chart_number": 1,
        "bar_index": 100,
        "bar_start_time": "2026-06-19 10:05:00",
        "trade_mode": "replay",
        "strategy_id": "price_only_vwap_reclaim",
        "signal_id": "price_only_vwap_reclaim_001",
        "direction": "long",
        "action": "candidate",
        "signal_price": 5500.25,
        "stop_price": 5496.25,
        "target_price": 5508.25,
        "invalidation_price": 5496.25,
        "rejection_reason": "not_applicable",
        "confidence": 0.5,
        "notes": "schema smoke row",
    }


def test_loads_signal_log_schema() -> None:
    schema = load_signal_log_schema()

    assert schema["profile_id"] == "axon_signal_log_v1"
    assert "event_key" in schema["csv"]["header"]
    assert "candidate_signal" in schema["event_types"]
    assert "rejected_signal" in schema["event_types"]


def test_signal_log_schema_is_internally_consistent() -> None:
    schema = load_yaml("config/research/signal_log_schema.yaml")

    validate_signal_log_schema(schema)

    header = set(schema["csv"]["header"])
    assert set(schema["common_required_fields"]).issubset(header)
    for fields in schema["event_type_required_fields"].values():
        assert set(fields).issubset(header)


def test_validates_candidate_signal_row() -> None:
    row = _candidate_row()

    assert validate_signal_log_row(row) == row


def test_validates_rejected_signal_row() -> None:
    row = _candidate_row()
    row.update(
        {
            "event_type": "rejected_signal",
            "action": "reject",
            "rejection_reason": "risk_limit",
            "stop_price": "",
            "target_price": "",
            "invalidation_price": "",
        },
    )

    assert validate_signal_log_row(row) == row


def test_rejects_candidate_missing_stop_target_or_invalidation() -> None:
    row = _candidate_row()
    row["stop_price"] = ""

    with pytest.raises(SignalLogError, match="stop_price"):
        validate_signal_log_row(row)


def test_rejects_invalid_enum_value() -> None:
    row = _candidate_row()
    row["direction"] = "sideways"

    with pytest.raises(SignalLogError, match="Invalid direction"):
        validate_signal_log_row(row)


def test_rejects_invalid_numeric_value() -> None:
    row = _candidate_row()
    row["signal_price"] = "not-a-price"

    with pytest.raises(SignalLogError, match="signal_price"):
        validate_signal_log_row(row)


def test_acsil_signal_logger_uses_schema_columns() -> None:
    source = open("src/acsil/OrderFlowSignalSmokeTest.cpp", encoding="utf-8").read()
    schema = load_signal_log_schema()

    for field_name in schema["csv"]["header"]:
        assert field_name in source

    assert 'EventType.SetString("candidate_signal")' in source


def test_acsil_liquidity_sweep_overlay_uses_signal_schema() -> None:
    source = open("src/acsil/AxonTradeLiquiditySweepSignalOverlay.cpp", encoding="utf-8").read()
    schema = load_signal_log_schema()

    for field_name in schema["csv"]["header"]:
        assert field_name in source

    assert "liquidity_sweep_absorption_reversal" in source
    assert "SC_BIDVOL" in source
    assert "SC_ASKVOL" in source
    assert "candidate_signal" in source
    assert "rejected_signal" in source
