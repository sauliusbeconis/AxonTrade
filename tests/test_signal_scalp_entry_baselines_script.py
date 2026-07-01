from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path


def _load_baseline_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_signal_scalp_entry_baselines.py"
    )
    spec = importlib.util.spec_from_file_location("run_signal_scalp_entry_baselines", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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


def test_feature_rows_compute_session_vwap_when_export_is_missing() -> None:
    module = _load_baseline_module()
    raw_rows = [
        _raw_row(volume=10, hlc_avg=100),
        _raw_row(volume=30, hlc_avg=110),
        _raw_row(volume=20, hlc_avg=90),
    ]
    normalized_rows = [
        _normalized_row(0, "2026-06-17 09:30:00", high=101, low=99, close=100),
        _normalized_row(1, "2026-06-17 09:33:00", high=111, low=109, close=110),
        _normalized_row(2, "2026-06-18 09:30:00", high=91, low=89, close=90),
    ]

    rows = module._feature_rows(raw_rows, normalized_rows)

    assert rows[0]["vwap"] == 100
    assert rows[0]["vwap_source"] == "computed_session"
    assert rows[1]["vwap"] == 107.5
    assert rows[2]["vwap"] == 90


def test_feature_rows_prefer_exported_vwap() -> None:
    module = _load_baseline_module()
    raw_rows = [_raw_row(volume=10, hlc_avg=100, vwap=99.25)]
    normalized_rows = [
        _normalized_row(0, "2026-06-17 09:30:00", high=101, low=99, close=100),
    ]

    rows = module._feature_rows(raw_rows, normalized_rows)

    assert rows[0]["vwap"] == 99.25
    assert rows[0]["vwap_source"] == "exported"


def test_parallel_output_mode_matches_single_process_sweep() -> None:
    module = _load_baseline_module()
    normalized_rows = [
        _normalized_row(0, "2026-06-17 10:00:00", high=100, low=99.5, close=100),
        _normalized_row(1, "2026-06-17 10:03:00", high=101.25, low=100.5, close=101),
        _normalized_row(2, "2026-06-17 10:06:00", high=102.25, low=101.5, close=102),
        _normalized_row(0, "2026-06-18 10:00:00", high=100, low=99.5, close=100),
        _normalized_row(1, "2026-06-18 10:03:00", high=99.5, low=98.75, close=99),
        _normalized_row(2, "2026-06-18 10:06:00", high=98.5, low=97.75, close=98),
    ]
    signals_by_strategy = {
        "strategy_a": [_candidate(0, "2026-06-17 10:00:00", "long", "strategy_a")],
        "strategy_b": [_candidate(3, "2026-06-18 10:00:00", "short", "strategy_b")],
    }
    kwargs = {
        "output_mode": "sweep",
        "normalized_rows": normalized_rows,
        "signals_by_strategy": signals_by_strategy,
        "first_target_points_values": [1],
        "stop_points_values": [2],
        "runner_target_points_values": [2],
        "runner_stop_modes": ["breakeven"],
        "instrument_root": "ES",
        "slippage_ticks_per_side": None,
        "slippage_ticks_per_contract": 1,
        "entry_match_mode": "timestamp",
        "train_date_count": 1,
        "holdout_date_count": 1,
        "minimum_train_trades": 1,
        "window_step_date_count": 1,
    }

    single_process_rows = module._run_output_mode(**kwargs, jobs=1)
    parallel_rows = module._run_output_mode(**kwargs, jobs=2)

    assert parallel_rows == single_process_rows


def test_resolve_jobs_caps_workers_to_task_count() -> None:
    module = _load_baseline_module()

    assert module._resolve_jobs(0, 3) == min(3, module.os.cpu_count() or 1)
    assert module._resolve_jobs(8, 3) == 3
    assert module._resolve_jobs(2, 1) == 1


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


def _raw_row(*, volume: float, hlc_avg: float, vwap: float | None = None) -> dict[str, str]:
    row = {
        "Volume": str(volume),
        "HLC Avg": str(hlc_avg),
        "# of Trades": "1",
        "Bid Volume": "1",
        "Ask Volume": "1",
        "Ask Volume Bid Volume Difference": "0",
        "Ask Volume Bid Volume Difference Change": "0",
    }
    if vwap is not None:
        row["VWAP"] = str(vwap)
    return row


def _candidate(
    bar_index: int,
    timestamp: str,
    direction: str,
    strategy_id: str,
) -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": f"ESU26-CME:{bar_index}:{strategy_id}:{direction}",
        "strategy_id": strategy_id,
        "signal_id": f"{strategy_id}_{bar_index}_{direction}",
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "bar_start_time": timestamp,
        "direction": direction,
        "signal_price": "100",
    }


def _normalized_row(
    bar_index: int,
    timestamp: str,
    *,
    high: float,
    low: float,
    close: float,
) -> dict[str, object]:
    return {
        "symbol": "ESU26-CME",
        "chart_number": "2",
        "bar_index": bar_index,
        "timestamp": timestamp,
        "session_phase": "rth",
        "open": close,
        "high": high,
        "low": low,
        "close": close,
    }
