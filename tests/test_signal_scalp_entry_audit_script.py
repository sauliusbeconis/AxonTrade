from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_signal_scalp_entry_audit.py"
    )
    spec = importlib.util.spec_from_file_location("run_signal_scalp_entry_audit", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_audits_generated_scalp_entry_selection() -> None:
    module = _load_audit_module()
    bars = [
        _bar(0, timestamp="2026-06-17 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-17 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-17 10:02:00", high=102.25, low=100.5, close=102),
    ]
    signal = _candidate()
    selection = {
        "split_id": "scaled_scalp_walk_forward_window=1:train_dates=1:holdout_dates=1",
        "sample": "holdout",
        "selected_on_train": "true",
        "trade_dates": "2026-06-17",
        "strategy_id": "test_strategy",
        "first_target_points": "1",
        "stop_points": "2",
        "runner_target_points": "2",
        "runner_stop_mode": "breakeven",
    }

    audit_rows = module.audit_generated_scalp_entry_selection(
        bars=bars,
        signals_by_strategy={"test_strategy": [signal]},
        selection_rows=[selection],
        samples=["holdout"],
        instrument_root=None,
        slippage_ticks_per_side=None,
        slippage_ticks_per_contract=None,
        entry_match_mode="auto",
    )

    assert list(audit_rows[0].keys()) == module.SIGNAL_SCALP_ENTRY_AUDIT_HEADER
    assert audit_rows[0]["sample_signal_occurrence"] == 1
    assert audit_rows[0]["sample_duplicate_signal"] == "false"
    assert audit_rows[0]["selected_first_target_points"] == "1"
    assert audit_rows[0]["exit_reason"] == "runner_target_hit"
    assert audit_rows[0]["first_target_hit"] == "true"
    assert audit_rows[0]["gross_usd"] == "150"
    assert audit_rows[0]["net_usd"] == "93"


def _bar(
    bar_index: int,
    *,
    timestamp: str,
    high: float,
    low: float,
    close: float,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "high": high,
        "low": low,
        "close": close,
    }


def _candidate() -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": "ESU26-CME:0:test_strategy:long:0",
        "strategy_id": "test_strategy",
        "signal_id": "test_strategy_2026-06-17_0_long_0",
        "symbol": "ESU26-CME",
        "bar_index": 0,
        "bar_start_time": "2026-06-17 10:00:00",
        "direction": "long",
        "signal_price": "100",
    }
