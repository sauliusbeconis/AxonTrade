from __future__ import annotations

import pytest

from axontrade.config import ConfigError
from axontrade.research import (
    ScaledContextGuardAcceptanceError,
    evaluate_scaled_context_guard_acceptance,
    load_scaled_context_guard_acceptance_config,
    render_scaled_context_guard_acceptance_report,
    scaled_context_guard_acceptance_passed,
    summarize_scaled_context_guard_acceptance_sample,
    validate_scaled_context_guard_acceptance_config,
)


def test_loads_default_scaled_context_guard_acceptance_config() -> None:
    config = load_scaled_context_guard_acceptance_config()

    assert config["profile_id"] == "scaled_context_guard_acceptance_gates_v1"
    assert config["candidate"]["guard_name"] == "lookback_fade_push_session_range_30_risk_avg_2.5"


def test_acceptance_passes_when_all_gates_pass() -> None:
    findings = evaluate_scaled_context_guard_acceptance(
        [_fixed_guard_row()],
        _robustness_rows(),
        config=_config(),
    )

    assert scaled_context_guard_acceptance_passed(findings)
    assert all(finding.passed for finding in findings)


def test_acceptance_fails_fragile_sample() -> None:
    fixed = _fixed_guard_row(kept_trades=40, net_usd=1000, profit_factor=1.05, drawdown=-900)
    robustness = _robustness_rows(guarded_net=-100, improvement=-50, negative_windows=4)

    findings = evaluate_scaled_context_guard_acceptance(
        [fixed],
        robustness,
        config=_config(),
    )
    summary = summarize_scaled_context_guard_acceptance_sample(
        [fixed],
        robustness,
        config=_config(),
    )
    by_gate = {finding.gate_id: finding for finding in findings}

    assert not scaled_context_guard_acceptance_passed(findings)
    assert by_gate["minimum_fixed_guard_trades"].passed is False
    assert by_gate["minimum_fixed_guard_net_usd"].passed is False
    assert by_gate["minimum_fixed_guard_profit_factor"].passed is False
    assert by_gate["maximum_fixed_guard_drawdown_to_net_ratio"].passed is False
    assert by_gate["all_robustness_guarded_net_positive"].passed is False
    assert by_gate["all_robustness_improved_vs_unguarded"].passed is False
    assert by_gate["maximum_robustness_negative_window_rate"].passed is False
    assert summary.additional_fixed_guard_trades_required == 10


def test_renders_scaled_context_guard_acceptance_report() -> None:
    findings = evaluate_scaled_context_guard_acceptance(
        [_fixed_guard_row()],
        _robustness_rows(),
        config=_config(),
    )
    summary = summarize_scaled_context_guard_acceptance_sample(
        [_fixed_guard_row()],
        _robustness_rows(),
        config=_config(),
    )

    report = render_scaled_context_guard_acceptance_report(
        findings,
        config=_config(),
        sources={"fixed_guards": "fixed.csv", "robustness": "robustness.csv"},
        sample_summary=summary,
    )

    assert "# Scaled Context Guard Acceptance Report" in report
    assert "| Overall status | PASS |" in report
    assert "| PASS | minimum_fixed_guard_trades | 100 | >= 50 |" in report
    assert "| Fixed kept trades | 100 |" in report


def test_rejects_invalid_scaled_context_guard_acceptance_config() -> None:
    config = _config()
    config["gates"]["maximum_robustness_negative_window_rate"] = 1.5

    with pytest.raises(ConfigError, match="maximum_robustness_negative_window_rate"):
        validate_scaled_context_guard_acceptance_config(config)


def test_rejects_missing_candidate_guard_row() -> None:
    with pytest.raises(ScaledContextGuardAcceptanceError, match="Expected exactly one"):
        evaluate_scaled_context_guard_acceptance([], _robustness_rows(), config=_config())


def _config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": "test_scaled_context_guard_acceptance",
        "candidate": {
            "guard_name": "candidate_guard",
            "conditions": [
                "lookback_directional_move_points <= -2.5",
                "session_range_points >= 30",
            ],
        },
        "gates": {
            "minimum_fixed_guard_trades": 50,
            "minimum_fixed_guard_net_usd": 5000,
            "minimum_fixed_guard_average_net_usd": 50,
            "minimum_fixed_guard_profit_factor": 1.2,
            "maximum_fixed_guard_drawdown_to_net_ratio": 0.30,
            "maximum_fixed_guard_worst_day_loss_usd": 2000,
            "minimum_robustness_rows": 2,
            "require_all_robustness_guarded_net_positive": True,
            "require_all_robustness_improved_vs_unguarded": True,
            "minimum_worst_robustness_guarded_net_usd": 1000,
            "minimum_worst_robustness_average_net_usd": 25,
            "maximum_robustness_negative_window_rate": 0.50,
            "maximum_worst_guarded_window_loss_usd": 2500,
        },
    }


def _fixed_guard_row(
    *,
    kept_trades: int = 100,
    net_usd: float = 10000,
    profit_factor: float = 1.4,
    drawdown: float = -1000,
) -> dict[str, str]:
    return {
        "guard_name": "candidate_guard",
        "conditions": "lookback_directional_move_points <= -2.5",
        "input_trades": "200",
        "kept_trades": str(kept_trades),
        "skipped_trades": str(200 - kept_trades),
        "net_usd": str(net_usd),
        "average_net_usd": str(net_usd / kept_trades),
        "profit_factor": str(profit_factor),
        "max_trade_sequence_drawdown_usd": str(drawdown),
        "worst_day": "2026-06-10",
        "worst_day_net_usd": "-1000",
    }


def _robustness_rows(
    *,
    guarded_net: float = 5000,
    improvement: float = 2500,
    negative_windows: int = 1,
) -> list[dict[str, str]]:
    return [
        _robustness_row(guarded_net, improvement, negative_windows),
        _robustness_row(guarded_net + 1000, improvement + 100, 0),
    ]


def _robustness_row(
    guarded_net: float,
    improvement: float,
    negative_windows: int,
) -> dict[str, str]:
    return {
        "holdout_windows": "4",
        "negative_holdout_windows": str(negative_windows),
        "guarded_holdout_net_usd": str(guarded_net),
        "guard_net_improvement_usd": str(improvement),
        "guarded_average_net_usd": "75",
        "worst_guarded_window_net_usd": "-1000",
    }
