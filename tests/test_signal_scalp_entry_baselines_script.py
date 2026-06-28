from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path


def _load_baseline_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_signal_scalp_entry_baselines.py"
    )
    spec = importlib.util.spec_from_file_location("run_signal_scalp_entry_baselines", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generates_session_structure_signals_without_scalp_defaults() -> None:
    module = _load_baseline_module()
    rows = [
        _feature_row(0, "2026-06-17 09:30:00", high=101, low=99, close=100),
        _feature_row(1, "2026-06-17 09:45:00", high=100.5, low=99.5, close=100),
        _feature_row(2, "2026-06-17 10:05:00", high=102, low=100, close=100.25),
        _feature_row(3, "2026-06-17 10:20:00", high=102, low=101, close=101.75),
    ]

    signals_by_strategy = module._generate_strategy_signals(
        rows,
        random_seed=1,
        random_per_day=1,
        max_rule_entries_per_day=10,
        minimum_spacing_seconds=0,
        entry_family_set="session",
    )

    assert "random_1_per_day" not in signals_by_strategy
    sweep_signals = signals_by_strategy["opening_range_sweep_fade_30m_0.5pt"]
    breakout_signals = signals_by_strategy["opening_range_breakout_continue_30m_0.5pt"]
    assert [signal["direction"] for signal in sweep_signals] == ["short"]
    assert [signal["direction"] for signal in breakout_signals] == ["long"]


def test_generates_vwap_reclaim_session_signal() -> None:
    module = _load_baseline_module()
    rows = [
        _feature_row(0, "2026-06-17 09:30:00", high=101, low=99, close=100, vwap=100),
        _feature_row(1, "2026-06-17 10:01:00", high=98, low=96.5, close=97, vwap=100),
        _feature_row(2, "2026-06-17 10:10:00", high=99.5, low=98.5, close=99, vwap=100),
        _feature_row(
            3,
            "2026-06-17 10:11:00",
            high=100.5,
            low=99.5,
            close=100.25,
            vwap=100,
            delta=10,
        ),
    ]

    signals_by_strategy = module._generate_strategy_signals(
        rows,
        random_seed=1,
        random_per_day=1,
        max_rule_entries_per_day=10,
        minimum_spacing_seconds=0,
        entry_family_set="session",
    )

    reclaim_signals = signals_by_strategy["vwap_reclaim_continue_15m_2pt"]
    assert len(reclaim_signals) == 1
    assert reclaim_signals[0]["direction"] == "long"
    assert reclaim_signals[0]["bar_index"] == 3


def _feature_row(
    bar_index: int,
    timestamp: str,
    *,
    high: float,
    low: float,
    close: float,
    vwap: float | None = None,
    delta: float = 0,
) -> dict[str, object]:
    parsed_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    close_location = 0.5 if high <= low else (close - low) / (high - low)
    return {
        "symbol": "ESU26-CME",
        "timestamp": timestamp,
        "bar_index": bar_index,
        "trade_date": parsed_timestamp.date().isoformat(),
        "parsed_timestamp": parsed_timestamp,
        "open_float": close,
        "high_float": high,
        "low_float": low,
        "close_float": close,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "bar_range": high - low,
        "vwap": close if vwap is None else vwap,
        "volume": 1,
        "trades": 1,
        "bid_volume": 1,
        "ask_volume": 1,
        "delta": delta,
        "delta_change": delta,
        "close_location": close_location,
    }
