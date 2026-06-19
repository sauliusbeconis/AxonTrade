from __future__ import annotations

import pytest

from axontrade.config import ConfigError
from axontrade.research import (
    AcceptanceGateError,
    evaluate_price_only_acceptance,
    load_price_only_acceptance_config,
    price_only_acceptance_passed,
    render_price_only_acceptance_report,
    validate_price_only_acceptance_config,
)


def test_loads_default_price_only_acceptance_config() -> None:
    config = load_price_only_acceptance_config()

    assert config["profile_id"] == "price_only_acceptance_gates_v1"
    assert config["gates"]["minimum_total_outcome_trades"] == 100


def test_acceptance_passes_when_all_gates_pass() -> None:
    findings = evaluate_price_only_acceptance(
        _outcomes(120),
        _daily_rows(20, losing_day_net=-100, losing_days=5),
        _selected_holdout_rows(12, net_usd=500, split_prefix="single"),
        _selected_holdout_rows(30, net_usd=1500, split_prefix="walk"),
        config=_config(),
    )

    assert price_only_acceptance_passed(findings)
    assert all(finding.passed for finding in findings)


def test_acceptance_fails_current_style_underpowered_sample() -> None:
    findings = evaluate_price_only_acceptance(
        _outcomes(47),
        [
            {"trade_date": "2026-06-10", "net_usd": "-4040.50"},
            {"trade_date": "2026-06-11", "net_usd": "-8881.00"},
            {"trade_date": "2026-06-12", "net_usd": "-5955.00"},
            {"trade_date": "2026-06-15", "net_usd": "2404.00"},
            {"trade_date": "2026-06-16", "net_usd": "-1226.50"},
            {"trade_date": "2026-06-17", "net_usd": "-99.50"},
            {"trade_date": "2026-06-18", "net_usd": "-353.50"},
        ],
        _selected_holdout_rows(0, net_usd=0, split_prefix="single"),
        _selected_holdout_rows(10, net_usd=-847.50, split_prefix="walk"),
        config=_config(),
    )

    by_gate = {finding.gate_id: finding for finding in findings}

    assert not price_only_acceptance_passed(findings)
    assert by_gate["minimum_total_outcome_trades"].passed is False
    assert by_gate["minimum_trade_days"].passed is False
    assert by_gate["minimum_walk_forward_holdout_trades"].passed is False
    assert by_gate["positive_walk_forward_holdout_net"].passed is False
    assert by_gate["minimum_selected_train_holdout_trades"].passed is False
    assert by_gate["maximum_worst_day_loss_share"].passed is False


def test_renders_price_only_acceptance_report() -> None:
    findings = evaluate_price_only_acceptance(
        _outcomes(1),
        [{"trade_date": "2026-06-19", "net_usd": "-100"}],
        _selected_holdout_rows(0, net_usd=0, split_prefix="single"),
        _selected_holdout_rows(0, net_usd=0, split_prefix="walk"),
        config=_config(),
    )

    report = render_price_only_acceptance_report(
        findings,
        config=_config(),
        sources={"outcomes": "outcomes.csv"},
    )

    assert "# Price-Only Acceptance Report" in report
    assert "| Overall status | FAIL |" in report
    assert "| FAIL | minimum_total_outcome_trades | 1 | >= 100 |" in report


def test_rejects_invalid_acceptance_config() -> None:
    config = _config()
    config["gates"]["maximum_worst_day_loss_share"] = 1.5

    with pytest.raises(ConfigError, match="maximum_worst_day_loss_share"):
        validate_price_only_acceptance_config(config)


def test_rejects_non_numeric_gate_inputs() -> None:
    with pytest.raises(AcceptanceGateError, match="net_usd"):
        evaluate_price_only_acceptance(
            _outcomes(100),
            [{"trade_date": "2026-06-19", "net_usd": "bad"}],
            _selected_holdout_rows(10, net_usd=0, split_prefix="single"),
            _selected_holdout_rows(30, net_usd=1, split_prefix="walk"),
            config=_config(),
        )


def _config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": "test_price_only_acceptance",
        "gates": {
            "minimum_total_outcome_trades": 100,
            "minimum_trade_days": 20,
            "minimum_walk_forward_holdout_trades": 30,
            "require_positive_walk_forward_holdout_net": True,
            "minimum_selected_train_holdout_trades": 10,
            "maximum_worst_day_loss_share": 0.40,
        },
    }


def _outcomes(count: int) -> list[dict[str, str]]:
    return [{"outcome_id": f"outcome-{index}"} for index in range(count)]


def _daily_rows(
    days: int,
    *,
    losing_day_net: float,
    losing_days: int,
) -> list[dict[str, str]]:
    rows = [
        {"trade_date": f"2026-06-{day:02d}", "net_usd": "100"}
        for day in range(1, days + 1)
    ]
    for row in rows[:losing_days]:
        row["net_usd"] = str(losing_day_net)
    return rows


def _selected_holdout_rows(
    trades: int,
    *,
    net_usd: float,
    split_prefix: str,
) -> list[dict[str, str]]:
    return [
        {
            "split_id": f"{split_prefix}-1",
            "sample": "holdout",
            "selected_on_train": "true",
            "evaluated_trades": str(trades),
            "net_usd": str(net_usd),
        },
    ]
