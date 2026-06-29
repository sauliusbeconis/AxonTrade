from __future__ import annotations

import pytest

from axontrade.config import ConfigError
from axontrade.research import (
    ScaledScalpAcceptanceError,
    evaluate_scaled_scalp_acceptance,
    load_scaled_scalp_acceptance_config,
    render_scaled_scalp_acceptance_report,
    scaled_scalp_acceptance_passed,
    summarize_scaled_scalp_acceptance_sample,
    validate_scaled_scalp_acceptance_config,
)


def test_loads_default_scaled_scalp_acceptance_config() -> None:
    config = load_scaled_scalp_acceptance_config()

    assert config["profile_id"] == "scaled_scalp_fixed_row_acceptance_gates_v1"
    assert config["gates"]["minimum_outcome_trades"] == 100


def test_acceptance_passes_when_all_gates_pass() -> None:
    findings = evaluate_scaled_scalp_acceptance(
        _outcome_rows(days=20, per_day=6, daily_net=100, direction="long"),
        _sweep_rows(positive_neighbors=4),
        holiday_dates=[],
        config=_config(),
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )

    assert scaled_scalp_acceptance_passed(findings)
    assert all(finding.passed for finding in findings)


def test_acceptance_fails_underpowered_unstable_short_sample() -> None:
    rows = (
        _outcome_rows(days=10, per_day=6, daily_net=-100, direction="short")
        + _outcome_rows(days=3, per_day=6, daily_net=900, direction="long", start_day=11)
    )

    findings = evaluate_scaled_scalp_acceptance(
        rows,
        _sweep_rows(positive_neighbors=2),
        holiday_dates=[],
        config=_config(),
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )
    summary = summarize_scaled_scalp_acceptance_sample(
        rows,
        _sweep_rows(positive_neighbors=2),
        holiday_dates=[],
        config=_config(),
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )
    by_gate = {finding.gate_id: finding for finding in findings}

    assert not scaled_scalp_acceptance_passed(findings)
    assert by_gate["minimum_outcome_trades"].passed is False
    assert by_gate["minimum_trade_dates"].passed is False
    assert by_gate["maximum_drawdown_to_net_ratio"].passed is False
    assert by_gate["maximum_last_n_positive_day_net_share"].passed is False
    assert by_gate["minimum_positive_nearby_parameter_rows"].passed is False
    assert by_gate["nonnegative_holiday_adjusted_short_net"].passed is False
    assert summary.additional_trades_required == 22
    assert summary.additional_trade_dates_required == 7


def test_renders_scaled_scalp_acceptance_report() -> None:
    rows = _outcome_rows(days=1, per_day=2, daily_net=50, direction="long")
    findings = evaluate_scaled_scalp_acceptance(
        rows,
        _sweep_rows(positive_neighbors=1),
        config=_config(),
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )
    summary = summarize_scaled_scalp_acceptance_sample(
        rows,
        _sweep_rows(positive_neighbors=1),
        config=_config(),
        first_target_points=5,
        stop_points=10,
        runner_target_points=8,
    )

    report = render_scaled_scalp_acceptance_report(
        findings,
        config=_config(),
        sources={"outcomes": "outcomes.csv"},
        sample_summary=summary,
    )

    assert "# Fixed Scaled-Scalp Acceptance Report" in report
    assert "| Overall status | FAIL |" in report
    assert "| FAIL | minimum_outcome_trades | 2 | >= 100 |" in report
    assert "| Additional trades required | 98 |" in report


def test_rejects_invalid_scaled_scalp_acceptance_config() -> None:
    config = _config()
    config["gates"]["maximum_drawdown_to_net_ratio"] = 1.5

    with pytest.raises(ConfigError, match="maximum_drawdown_to_net_ratio"):
        validate_scaled_scalp_acceptance_config(config)


def test_rejects_bad_outcome_net() -> None:
    rows = _outcome_rows(days=1, per_day=1, daily_net=100, direction="long")
    rows[0]["net_usd"] = "bad"

    with pytest.raises(ScaledScalpAcceptanceError, match="net_usd"):
        evaluate_scaled_scalp_acceptance(
            rows,
            _sweep_rows(positive_neighbors=4),
            config=_config(),
            first_target_points=5,
            stop_points=10,
            runner_target_points=8,
        )


def _config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": "test_scaled_scalp_acceptance",
        "gates": {
            "minimum_outcome_trades": 100,
            "minimum_trade_dates": 20,
            "require_positive_holiday_adjusted_net": True,
            "require_positive_holiday_adjusted_fixed_rolling_holdout_net": True,
            "maximum_drawdown_to_net_ratio": 0.50,
            "last_n_dates": 3,
            "maximum_last_n_positive_day_net_share": 0.40,
            "minimum_positive_nearby_parameter_rows": 4,
            "require_nonnegative_holiday_adjusted_short_net": True,
            "maximum_nonholiday_terminal_exits": 0,
        },
    }


def _outcome_rows(
    *,
    days: int,
    per_day: int,
    daily_net: float,
    direction: str,
    start_day: int = 1,
) -> list[dict[str, str]]:
    rows = []
    net_per_trade = daily_net / per_day
    for day in range(start_day, start_day + days):
        for index in range(per_day):
            rows.append(
                {
                    "entry_time": f"2026-06-{day:02d} 10:{index:02d}:00",
                    "direction": direction,
                    "exit_reason": "runner_target_hit" if net_per_trade >= 0 else "full_stop_hit",
                    "net_usd": str(net_per_trade),
                },
            )
    return rows


def _sweep_rows(*, positive_neighbors: int) -> list[dict[str, str]]:
    positive = [
        _sweep(5, 10, 8, 100),
        _sweep(4, 10, 8, 50),
        _sweep(5, 8, 8, 25),
        _sweep(5, 10, 10, 10),
    ][:positive_neighbors]
    negative = [
        _sweep(4, 8, 8, -100),
        _sweep(4, 10, 10, -100),
        _sweep(5, 8, 10, -100),
    ]
    return positive + negative


def _sweep(
    first_target: float,
    stop: float,
    runner_target: float,
    net_usd: float,
) -> dict[str, str]:
    return {
        "direction_filter": "all",
        "first_target_points": str(first_target),
        "stop_points": str(stop),
        "runner_target_points": str(runner_target),
        "runner_stop_mode": "initial",
        "net_usd": str(net_usd),
    }
