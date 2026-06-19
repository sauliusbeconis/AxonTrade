from __future__ import annotations

import pytest

from axontrade.research import (
    LiquiditySweepAbsorptionError,
    evaluate_liquidity_sweep_absorption_reversal,
    load_liquidity_sweep_absorption_config,
    validate_liquidity_sweep_absorption_config,
)


def _bar(
    bar_index: int,
    *,
    close: float,
    high: float,
    low: float,
    bid_volume: float,
    ask_volume: float,
    delta: float | None = None,
    timestamp: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "timestamp": timestamp or f"2026-06-19 10:{30 + bar_index:02d}:00",
        "symbol": "ESU26-CME",
        "chart_number": 1,
        "bar_index": bar_index,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "vwap": 100.0,
        "opening_range_high": 100.0,
        "opening_range_low": 90.0,
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "volume": "",
        "session_phase": "rth",
    }
    if delta is not None:
        row["delta"] = delta
    return row


def test_loads_liquidity_sweep_absorption_config() -> None:
    config = load_liquidity_sweep_absorption_config()

    assert config["strategy_id"] == "liquidity_sweep_absorption_reversal"
    assert config["outputs"]["no_absorption_rejection_reason"] == "no_absorption"


def test_liquidity_sweep_absorption_config_is_valid() -> None:
    validate_liquidity_sweep_absorption_config(load_liquidity_sweep_absorption_config())


def test_accepts_short_sweep_with_buying_absorbed() -> None:
    signals = evaluate_liquidity_sweep_absorption_reversal(
        [
            _bar(
                0,
                close=99.25,
                high=101.25,
                low=98.0,
                bid_volume=80,
                ask_volume=120,
            ),
        ],
    )

    assert signals[0]["event_type"] == "candidate_signal"
    assert signals[0]["direction"] == "short"
    assert signals[0]["rejection_reason"] == "not_applicable"
    assert "short absorption proxy" in signals[0]["notes"]


def test_accepts_long_sweep_with_selling_absorbed() -> None:
    signals = evaluate_liquidity_sweep_absorption_reversal(
        [
            _bar(
                0,
                close=90.75,
                high=92.0,
                low=88.75,
                bid_volume=130,
                ask_volume=80,
            ),
        ],
    )

    assert signals[0]["event_type"] == "candidate_signal"
    assert signals[0]["direction"] == "long"
    assert "long absorption proxy" in signals[0]["notes"]


def test_rejects_sweep_without_sweep_side_aggression() -> None:
    signals = evaluate_liquidity_sweep_absorption_reversal(
        [
            _bar(
                0,
                close=99.25,
                high=101.25,
                low=98.0,
                bid_volume=130,
                ask_volume=80,
            ),
        ],
    )

    assert signals[0]["event_type"] == "rejected_signal"
    assert signals[0]["rejection_reason"] == "no_absorption"
    assert "failed=delta,aggression_ratio" in signals[0]["notes"]


def test_rejects_sweep_when_close_favors_aggressor() -> None:
    signals = evaluate_liquidity_sweep_absorption_reversal(
        [
            _bar(
                0,
                close=99.75,
                high=101.25,
                low=98.0,
                bid_volume=80,
                ask_volume=120,
            ),
        ],
    )

    assert signals[0]["event_type"] == "rejected_signal"
    assert signals[0]["rejection_reason"] == "no_absorption"
    assert "close_location" in signals[0]["notes"]


def test_rejects_duplicate_absorption_signal_per_side_per_day() -> None:
    signals = evaluate_liquidity_sweep_absorption_reversal(
        [
            _bar(0, close=99.25, high=101.25, low=98.0, bid_volume=80, ask_volume=120),
            _bar(1, close=99.25, high=101.5, low=98.0, bid_volume=75, ask_volume=120),
        ],
    )

    assert signals[0]["event_type"] == "candidate_signal"
    assert signals[1]["event_type"] == "rejected_signal"
    assert signals[1]["rejection_reason"] == "duplicate_signal"


def test_rejects_missing_bid_ask_fields() -> None:
    row = _bar(0, close=99.5, high=101.25, low=98.0, bid_volume=80, ask_volume=120)
    del row["ask_volume"]

    with pytest.raises(LiquiditySweepAbsorptionError, match="ask_volume"):
        evaluate_liquidity_sweep_absorption_reversal([row])
