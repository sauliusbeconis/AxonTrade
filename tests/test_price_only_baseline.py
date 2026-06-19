from __future__ import annotations

import csv

import pytest

from axontrade.config import load_yaml
from axontrade.research import (
    BaselineError,
    evaluate_price_only_vwap_reclaim,
    load_price_only_bar_rows_csv,
    load_price_only_baseline_config,
    validate_price_only_baseline_config,
)


def _bar(
    bar_index: int,
    close: float,
    vwap: float,
    *,
    symbol: str = "ESU26-CME",
    high: float | None = None,
    low: float | None = None,
    session_phase: str = "rth",
) -> dict[str, object]:
    return {
        "timestamp": f"2026-06-19 09:{30 + bar_index:02d}:00",
        "symbol": symbol,
        "chart_number": 1,
        "bar_index": bar_index,
        "open": close - 0.5,
        "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1,
        "close": close,
        "vwap": vwap,
        "opening_range_high": 100.0,
        "opening_range_low": 90.0,
        "session_phase": session_phase,
    }


def test_loads_price_only_baseline_config() -> None:
    config = load_price_only_baseline_config()

    assert config["strategy_id"] == "price_only_vwap_opening_range_reclaim"
    assert config["default_trade_mode"] == "research"


def test_price_only_baseline_config_is_valid() -> None:
    config = load_yaml("config/research/price_only_vwap_reclaim.yaml")

    validate_price_only_baseline_config(config)


def test_emits_long_candidate_signal_after_vwap_and_opening_range_reclaim() -> None:
    rows = [
        _bar(0, close=99.0, vwap=100.0),
        _bar(1, close=101.0, vwap=100.0, low=99.5),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert signals[0]["event_type"] == "rejected_signal"
    assert signals[0]["rejection_reason"] == "insufficient_context"
    assert signals[1]["event_type"] == "candidate_signal"
    assert signals[1]["direction"] == "long"
    assert signals[1]["action"] == "candidate"
    assert float(signals[1]["stop_price"]) < float(signals[1]["signal_price"])
    assert float(signals[1]["target_price"]) > float(signals[1]["signal_price"])
    assert signals[1]["rejection_reason"] == "not_applicable"


def test_emits_short_candidate_signal_after_vwap_and_opening_range_reclaim() -> None:
    rows = [
        _bar(0, close=91.0, vwap=90.0),
        _bar(1, close=89.0, vwap=90.0, high=90.5),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert signals[1]["event_type"] == "candidate_signal"
    assert signals[1]["direction"] == "short"
    assert float(signals[1]["stop_price"]) > float(signals[1]["signal_price"])
    assert float(signals[1]["target_price"]) < float(signals[1]["signal_price"])


def test_emits_no_setup_rejection_when_reclaim_conditions_are_absent() -> None:
    rows = [
        _bar(0, close=99.0, vwap=100.0),
        _bar(1, close=99.5, vwap=100.0),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert signals[1]["event_type"] == "rejected_signal"
    assert signals[1]["action"] == "reject"
    assert signals[1]["rejection_reason"] == "no_setup"
    assert signals[1]["direction"] == "none"


def test_emits_outside_session_rejection() -> None:
    rows = [
        _bar(0, close=99.0, vwap=100.0),
        _bar(1, close=101.0, vwap=100.0, session_phase="eth"),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert signals[1]["event_type"] == "rejected_signal"
    assert signals[1]["rejection_reason"] == "outside_session"


def test_preserves_chronological_input_order() -> None:
    rows = [
        _bar(0, close=99.0, vwap=100.0),
        _bar(1, close=99.5, vwap=100.0),
        _bar(2, close=101.0, vwap=100.0),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert [signal["bar_index"] for signal in signals] == [0, 1, 2]
    assert [signal["event_type"] for signal in signals] == [
        "rejected_signal",
        "rejected_signal",
        "candidate_signal",
    ]


def test_tracks_previous_bar_context_per_symbol() -> None:
    rows = [
        _bar(0, close=99.0, vwap=100.0, symbol="ESU26-CME"),
        _bar(1, close=101.0, vwap=100.0, symbol="MESU26-CME"),
        _bar(2, close=101.0, vwap=100.0, symbol="ESU26-CME"),
    ]

    signals = evaluate_price_only_vwap_reclaim(rows)

    assert signals[1]["symbol"] == "MESU26-CME"
    assert signals[1]["rejection_reason"] == "insufficient_context"
    assert signals[2]["symbol"] == "ESU26-CME"
    assert signals[2]["event_type"] == "candidate_signal"


def test_loads_exported_bar_rows_from_csv(tmp_path) -> None:
    csv_path = tmp_path / "bars.csv"
    rows = [_bar(0, close=99.0, vwap=100.0), _bar(1, close=101.0, vwap=100.0)]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    loaded_rows = load_price_only_bar_rows_csv(csv_path)
    signals = evaluate_price_only_vwap_reclaim(loaded_rows)

    assert len(loaded_rows) == 2
    assert signals[1]["event_type"] == "candidate_signal"


def test_rejects_missing_required_bar_fields() -> None:
    row = _bar(0, close=99.0, vwap=100.0)
    del row["vwap"]

    with pytest.raises(BaselineError, match="vwap"):
        evaluate_price_only_vwap_reclaim([row])
