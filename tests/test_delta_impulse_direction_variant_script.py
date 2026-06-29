from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / (
        "run_delta_impulse_direction_variant_diagnostics.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_delta_impulse_direction_variant_diagnostics",
        script_path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_inverts_candidate_signal_directions() -> None:
    module = _load_module()

    rows = module.invert_candidate_signal_directions(
        [
            {
                "event_type": "candidate_signal",
                "event_key": "key-long",
                "strategy_id": "delta",
                "signal_id": "signal-long",
                "direction": "long",
                "notes": "long setup",
            },
            {
                "event_type": "candidate_signal",
                "event_key": "key-short",
                "strategy_id": "delta",
                "signal_id": "signal-short",
                "direction": "short",
                "notes": "short setup",
            },
            {
                "event_type": "rejected_signal",
                "event_key": "key-reject",
                "strategy_id": "delta",
                "signal_id": "signal-reject",
                "direction": "none",
            },
        ],
    )

    assert [row["direction"] for row in rows] == ["short", "long"]
    assert rows[0]["strategy_id"] == "delta_inverted_fade"
    assert rows[0]["signal_id"] == "signal-long_inverted_fade"
    assert rows[0]["event_key"] == "key-long:inverted_fade"
    assert rows[0]["notes"].startswith("inverted fade test;")


def test_renders_direction_variant_report() -> None:
    module = _load_module()

    report = module.render_direction_variant_report(
        bars_source="bars.txt",
        signal_log_source="signals.csv",
        logged_sweep=[
            _sweep_row("all", 1, 2, 3, "initial", 10, -100, 0.4),
            _sweep_row("long", 1, 2, 3, "initial", 5, -200, 0.2),
        ],
        inverted_sweep=[
            _sweep_row("all", 1, 2, 3, "initial", 10, 300, 0.6),
            _sweep_row("short", 1, 2, 3, "initial", 5, 100, 0.4),
        ],
        logged_walk_forward=[
            _walk_row("train", "2026-06-10", 10, 300),
            _walk_row("holdout", "2026-06-11", 5, -100),
        ],
        inverted_walk_forward=[
            _walk_row("train", "2026-06-10", 10, 500),
            _walk_row("holdout", "2026-06-11", 5, -50),
        ],
        logged_sweep_source="logged.csv",
        inverted_sweep_source="inverted.csv",
        logged_walk_forward_source="logged-wf.csv",
        inverted_walk_forward_source="inverted-wf.csv",
        train_date_count=20,
        holdout_date_count=5,
        minimum_train_trades=20,
        window_step_date_count=5,
    )

    assert "# Sierra Delta Impulse Direction Variant Diagnostics" in report
    assert "| Logged | 1 | 5 | -100 |" in report
    assert "| Inverted | 1 | 5 | -50 |" in report
    assert "positive in-sample rows" in report


def _sweep_row(
    direction: str,
    first_target: float,
    stop: float,
    runner_target: float,
    runner_stop_mode: str,
    trades: int,
    net_usd: float,
    positive_rate: float,
) -> dict[str, object]:
    return {
        "direction_filter": direction,
        "first_target_points": str(first_target),
        "stop_points": str(stop),
        "runner_target_points": str(runner_target),
        "runner_stop_mode": runner_stop_mode,
        "evaluated_trades": str(trades),
        "net_usd": str(net_usd),
        "positive_net_rate": str(positive_rate),
    }


def _walk_row(sample: str, dates: str, trades: int, net_usd: float) -> dict[str, object]:
    row = _sweep_row("all", 1, 2, 3, "initial", trades, net_usd, 0.5)
    row.update({"sample": sample, "trade_dates": dates})
    return row
